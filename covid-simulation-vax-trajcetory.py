#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pygame
import random
import networkx as nx
import matplotlib.pyplot as plt
from enum import Enum
import pydot
from networkx.drawing.nx_pydot import graphviz_layout
import json
import time
# Propagation/Cascading Network
G=nx.DiGraph(name='G')
# Trajectory Network | Tracks nodes that came within close proximity at one point
P=nx.Graph(name='P')

VC=nx.Graph(name='VC')
VC_CA=nx.Graph(name='VC_CA')

random.seed(2225) #77%
# random.seed(53236) #95%
# random.seed(1000012) #96%
# random.seed(1000014) #66%
# random.seed(1036) #66%

# constants
WIDTH, HEIGHT = 1200,900
WIN = pygame.display.set_mode([WIDTH, HEIGHT])
WHITE = (255,255,255)
FPS = 100
NODES = 99
NODE_SIZE = 20
INITIAL_INFECTIONS = 1
INITIAL_INFECTION = 8
RECOVERY_TIME = 750
IMMUNITY = 0.95
TS = 100
RETURNING_HOME = 100 #/1000
GOING_PUBLIC = 10  #/1000
pubsurfs = [(300,225),(700,225),(300,475),(700,475)]
graphstamps = []
TIME_IMPLEMENTED = 3000
TRAJECTORY_FILE = open("images/trajectories.json")
TRAJECTORIES = json.loads(TRAJECTORY_FILE.read())

class Vulnerability(Enum):
    LOW = [(10,13),(0.97,1), (1000,100), (0,128,255)]#(0,255,0)
    MEDIUM = [(14,17),(0.95,0.97), (1200,150), (0,128,255)]
    HIGH = [(18,21),(0.93,0.95), (1400,300),(0,128,255)] #(255,128,0)
    
    
class State(Enum):
    SUSCEPTIBLE = 1
    INFECTIOUS = 2
    RECOVERED = 3

def get_vulnerability(i):

    p = random.random()
    if(i<33):
        return Vulnerability.MEDIUM
    elif(i<66):
        return Vulnerability.LOW
    else:
        return Vulnerability.HIGH


class Node(pygame.sprite.Sprite):
    def __init__(self, pos_x,pos_y,id, home):
        super().__init__()
        self.id = id
        self.vulnerability = get_vulnerability(self.id)
        self.width = random.randint(self.vulnerability.value[0][0],self.vulnerability.value[0][1])
        self.image = pygame.Surface([self.width, self.width])
        self.image.fill(self.vulnerability.value[3])
        # self.image.fill((0,0,255))
        self.rect = self.image.get_rect()
        self.rect.center = [pos_x, pos_y]
        self.home = home
        self.public_dest = random.randint(0,3)
        self.destination = (random.randint(self.home[0],(self.home[0]+100)),random.randint(self.home[1],(self.home[1]+100)))
        self.reached_x = False
        self.reached_y = False
        self.state = State.SUSCEPTIBLE
        self.is_vaccinated = False
        self.antibodies = 0.0
        self.is_home = True
        self.days_infected = -1
        self.immunity = random.uniform(self.vulnerability.value[1][0],self.vulnerability.value[1][1])
        self.recovery_time = random.randint(self.vulnerability.value[2][0]-self.vulnerability.value[2][1],self.vulnerability.value[2][0]+self.vulnerability.value[2][1])
        self.trajectory = TRAJECTORIES[str(self.id)]
    
    def infect(self, received_from):
        if self.state == State.SUSCEPTIBLE:
            self.state = State.INFECTIOUS
            self.image.fill((255,0,0))
            
            if received_from == None:
                G.add_node(self.id, data = self)
                
            else:
                if not G.has_node(received_from.id):
                    G.add_node(received_from.id, data = received_from)
                if not G.has_node(self.id):
                    G.add_node(self.id, data = self)
                G.add_edge(received_from.id,self.id)
                P[received_from.id][self.id]['color'] = 'red'
            
    
    def recover(self):
        if self.state == State.INFECTIOUS:
            self.state = State.RECOVERED
#             self.infected = False
#             self.recovered = True
            self.image.fill((0,0,0))
#             self.immunity = 2
            self.antibodies = 0.1

    def vaccinate(self):
        self.antibodies = 0.1
        self.is_vaccinated = True
        if self.state == State.SUSCEPTIBLE:
            self.image.fill((232, 232, 28))

        
        
pygame.init()
# time.sleep(15)
all_nodes = []


# CREATE SURFACE

homes = []


home = pygame.Surface([100,100])
home.fill((140, 145, 140))

public = pygame.Surface([200,200])
public.fill((211, 222, 118))


y=60
x=60

while x <= 1040:
    homes.append((x,60))
    homes.append((x,740))
    x+=163
while y < 610:
    y+=110
    homes.append((60,y))
    homes.append((1040,y))
    
def main():
    
    # variable initialization
    timestep = 0
    t = 0
    nodes = []
    node_group = pygame.sprite.Group()
    infected_nodes = []
    recovered_nodes = []
    i_nodes = []
    r0 = []
    infections_ts = []
    
#     CREATE INITIAL NODES
    for i in range(NODES):
        h = i % len(homes)
        h = homes[h]
        obj = Node(random.randint(h[0],(h[0]+100)),random.randint(h[1],(h[1]+100)),i, h)
        if i >= INITIAL_INFECTION and i < INITIAL_INFECTION + INITIAL_INFECTIONS:
            obj.infect(None)
            infected_nodes.append(obj)
            i_nodes.append(obj.id)
            obj.is_home = False
        node_group.add(obj)
        nodes.append(obj)

    
#  Initialize Vaccination Compliance Graph
# node initialization
    for n in nodes:
        VC.add_node(n.id, data=n)
        VC_CA.add_node(n.id, data=n)
# edge initialization
    for n1 in VC:
        for n2 in VC:
            if n1 == n2:
                continue
            if not VC_CA.has_edge(n1,n2):
                VC_CA.add_edge(n1,n2)
            if not VC.has_edge(n1,n2):
                if VC.nodes[n1]['data'].public_dest == VC.nodes[n2]['data'].public_dest:
                    VC.add_edge(n1,n2, influence = 0.0)
                elif n1%len(homes) == n2%len(homes):
                    VC.add_edge(n1,n2, influence = 0.0)

# edge weight adjustment
    for n in VC:
        neighbors = list(VC.neighbors(n))
        house_mates = 0
        public_mates = 0
        for ni in neighbors:
            if n%len(homes) == ni%len(homes):
                house_mates += 1
            else:
                public_mates += 1
        for ni in neighbors:
            if n%len(homes) == ni%len(homes):
                VC[n][ni]["influence"] = float(0.5/house_mates)
            else:
                VC[n][ni]["influence"] = float(0.5/public_mates)
              

    #     set thresholds
    sigma = 0.33
    mu = 0.40
    for n in VC:
        thresh = random.normalvariate(mu, sigma)
        if thresh<0:
            thresh = 0
        elif thresh>1:
            thresh=1
        VC.nodes[n]['t'] = thresh
        VC_CA.nodes[n]['t'] = thresh
           


    def get_threshold_complete_graph(graph):
        an = 0.0
        for n in graph:
            if graph.nodes[n]['data'].is_vaccinated:
                an+=1.0
        return an/float(graph.number_of_nodes())
    
    def get_linear_threshold_node(graph, node):
        an = 0.0
        neighbors = list(graph.neighbors(node))
        for n in neighbors:
            if graph.nodes[n]['data'].is_vaccinated:
                an += graph[n][node]["influence"]
        return an
            



    
    running = True
    clock = pygame.time.Clock()
    all_nodes = nodes
    
    
# TIMESTAMP DATA TRACKING
    
    def save_g(time):
        color_map = []
        for node in G:       
            node = G.nodes[node]['data']
            if node.recovered:
                color_map.append('green')
            else:
                color_map.append('red')
        pos = graphviz_layout(G, prog="twopi")
        plt.figure(figsize=(10,10))
        print(time)
        plt.title('t = '+str(t)+' | R0 = ' + str(round(get_R0(),3)))
        nx.draw(G,pos, node_color=color_map, with_labels = True)
        plt.savefig('images/propagation'+str(int(time))+'.png')
        plt.clf()
        
    def r0_graph():
        print(r0)
        ts = [x for x, y in r0]
        data = [y for x, y in r0]
        (ax1, ax2) = plt.subplots(ncols=1, figsize=(10, 10))
        plt.plot(ts,data)
        plt.title("R0 values")
        ax2.set_xlabel('Time Stamp')
        ax2.set_ylabel('R0')
        plt.savefig("images/r0.png")
        plt.show()
        

    def infections_graph():
        print(infections_ts)
        ts = [x for x, y in infections_ts]
        data = [y for x, y in infections_ts]
        (ax1, ax2) = plt.subplots(ncols=1, figsize=(10, 10))
        plt.plot(ts,data)
        plt.title("Infections Over Time")
        ax2.set_xlabel('Time Stamp')
        ax2.set_ylabel('Infections')
        plt.savefig("images/infections.png")
        plt.show()
    
    def graphts():
        g = G.copy()
        pg = P.copy()
        vc = VC.copy()
        for u in g:
            g.nodes[u]['state']=g.nodes[u]['data'].state
        for u in pg:
            pg.nodes[u]['pub']=pg.nodes[u]['data'].public_dest
        for u in vc:
            vc.nodes[u]['is_vaccinated']=vc.nodes[u]['data'].is_vaccinated
        graphstamps.append((g,pg,vc))
        
    def vax_compliance_CA(ts):
        x = get_threshold_complete_graph(VC_CA)
        differences = 0
        for n in VC_CA:
            if VC_CA.nodes[n]['t']<=x and not VC_CA.nodes[n]['data'].is_vaccinated:
                differences += 1
                VC_CA.nodes[n]['data'].is_vaccinated = True
                VC_CA.nodes[n]['time'] = ts
        return differences
    
    
    def vax_compliance_LT(ts):
        differences = 0
        for n in VC:
            x = get_linear_threshold_node(VC, n)
            if VC.nodes[n]['t']<=x and not VC.nodes[n]['data'].is_vaccinated:
                differences += 1
                VC.nodes[n]['data'].vaccinate()
                VC.nodes[n]['time'] = ts
                
        return differences
    
    while running:
        
#         STOP RUNNING IF THERE IS NO MORE INFECTED NODES
        if len(infected_nodes) == 0:
            fts = open("images/vax_ts.txt", "w")
            fts.write(str(t))
            fts.close()
            graphts()
            print(get_threshold_complete_graph(VC))
            running = False
            pygame.quit()
            post_quit()
            exit()
            
        if (t % TS) == 0:
            graphts()
            
        if (t%600)==0:
            if t>=TIME_IMPLEMENTED:
                vax_compliance_LT(t)
            
        
        
        if (t % 100) == 0:
            r0.append((t,round(get_R0(),3)))
            infections_ts.append((t,len(infected_nodes)))
        t+=1
        
        
        
        
        
        # event loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print(get_threshold_complete_graph(VC))
                running = False
                pygame.quit()
                post_quit()
                exit()
        
        def proximity_add_edge(n1,n2):
            if n1.id==n2.id:
                return
            if not P.has_edge(n1.id,n2.id):
                if not P.has_node(n1.id):
                    P.add_node(n1.id, data = n1)
                if not P.has_node(n2.id):
                    P.add_node(n2.id, data = n2)
                P.add_edge(n1.id,n2.id)
                P[n1.id][n2.id]['weight'] = 1
                P[n1.id][n2.id]['color'] = 'grey'
                P[n1.id][n2.id]['contacts'] = [t]
                
            elif P.has_edge(n1.id,n2.id) and (t not in P[n1.id][n2.id]['contacts']):
                P[n1.id][n2.id]['weight'] += 1
                P[n1.id][n2.id]['contacts'].append(t)


        
        # collisions and infections LLL
        to_infect = []
        
        for node in nodes:
            collisions = pygame.sprite.spritecollide(node, node_group, False)
            if len(collisions) > 1:
                for i in range(len(collisions)):
                    proximity_add_edge(node,collisions[i])
                    # add edge to proximity graph
        
        for infected in infected_nodes:
            collisions = pygame.sprite.spritecollide(infected, node_group, False)
            if len(collisions) > 1:
                for i in range(len(collisions)):
                    # add edge to proximity graph
                    if (collisions[i].state == State.SUSCEPTIBLE) and random.random() >= (collisions[i].immunity + collisions[i].antibodies):
                        to_infect.append((infected,collisions[i]))
        

                    


        for n in to_infect:
            n[1].infect(n[0])
            infected_nodes.append(n[1])
            i_nodes.append(n[1].id)


        # node recovery
        for n in infected_nodes:
            if n.days_infected >= n.recovery_time:
                n.recover()
                infected_nodes.remove(n)
                recovered_nodes.append(n)
            else:
                n.days_infected += 1

        # graphics
        WIN.fill(WHITE)
        
#         INITIAL HOME PLACEMENT
        y=60
        x=60
        while x <= 1040:

            WIN.blit(home, (x,60))
            WIN.blit(home, (x,740))
            x+=163
        while y < 610:
            y+=110
            WIN.blit(home, (60,y))
            WIN.blit(home, (1040,y))
        
        for i in range(len(pubsurfs)):
            WIN.blit(public,pubsurfs[i])

        
        for n in node_group:
            if t <= len(n.trajectory):
                n.rect.center = n.trajectory[t]
                continue
            if n.rect.center[0] != n.destination[0] and n.reached_x==False:
                x = n.rect.center[0]
                y = n.rect.center[1]
                h = n.home
                direction = (n.destination[0]-n.rect.center[0])/abs(n.destination[0]-n.rect.center[0])
                inPublic = ((x > 171) and (x < 1029)) and ((y >171) and (y<729))
                inHousesX = ((x + direction) <= 171) or  ((x + direction) >= 1029)
                canEnter = ((y > (h[1] - 13)) and (y < (h[1] + 113)))
                
                if inPublic and inHousesX:
                    if canEnter:
                        n.rect.right += direction
                else:
                    n.rect.right += direction
            else:
                n.reached_x = True
            if n.rect.center[1] != n.destination[1] and n.reached_y==False:
                x = n.rect.center[0]
                y = n.rect.center[1]
                h = n.home
                direction = (n.destination[1]-n.rect.center[1])/abs(n.destination[1]-n.rect.center[1])
                inPublic = ((x > 171) and (x < 1029)) and ((y >171) and (y<729))
                inHousesY = ((y + direction) <= 171) or  ((y + direction) >= 729)
                canEnter = ((x > (h[0] - 13)) and (x < (h[0] + 113)))
                
                if inPublic and inHousesY:
                    if canEnter:
                        n.rect.bottom += direction
                else:
                    n.rect.bottom += direction

            else:
                n.reached_y = True
            if n.reached_x and n.reached_y:
                l = 100
                if n.is_home:
                    p = random.randint(0,1000)
#                 chance of leaving home
                    if p <= GOING_PUBLIC:
                        n.is_home = False
                        l = 200
                        h = pubsurfs[n.public_dest]
                    else:
                        h = n.home
                        l = 100
                else:
                    p = random.randint(0,1000)
#                     chance of returning home
                    if p <= RETURNING_HOME:
                        n.is_home = True
                        l = 100
                        h = n.home
                    else:
                        l=200
                        h = pubsurfs[n.public_dest]
                n.destination = (random.randint(h[0],(h[0]+l)),random.randint(h[1],(h[1]+l)))
                n.reached_x = n.destination[0] == n.rect.center[0]
                n.reached_y = n.destination[1] == n.rect.center[1]

        node_group.draw(WIN)
        pygame.display.flip()
        clock.tick(FPS)
        
        
        
        
        
        
        
        
        
        
#  ################################################################################################################
###################################################################################################################
#  ################################################################################################################
###################################################################################################################        
#  ################################################################################################################
###################################################################################################################        
        
        
        
        
        
        
        
        

def post_quit():
    percent_infected()
    create_tsgraphs()
    print('done')

    


def create_tsgraphs():
    i=-1
    for x in graphstamps:
        i+=1
        g = x[0]
        p = x[1]
        vc = x[2]
        fp = open("images/vax_graphP"+ str((TS*i)) +".json", "w")
        fg = open("images/vax_graphG"+ str((TS*i)) +".json", "w")
        fvc = open("images/vax_graphVC"+ str((TS*i)) +".json", "w")
        for u,v in p.edges():
            col = p[u][v]['color']
            w = p[u][v]['weight']
            c = p[u][v]['contacts']
            pubu = p.nodes[u]['pub']
            pubv = p.nodes[v]['pub']
            ob = {'u': u, 'v': v, 'weight': w, 'color':col, 'u_public': pubu, 'v_public': pubv, 'contacts': c}
            json_obj = json.dumps(ob)
            fp.write(json_obj+'\n')
            
        for u,v in g.edges():
            su = str(g.nodes[u]['state'])
            sv = str(g.nodes[v]['state'])
            ob = {'u': u, 'v': v, 'u_state': su, 'v_state': sv}
            json_obj = json.dumps(ob)
            fg.write(json_obj+'\n')
        for u,v in vc.edges():
            su = vc.nodes[u]['is_vaccinated']
            sv = vc.nodes[v]['is_vaccinated']
            ob = {'u': u, 'v': v, 'u_vaxxed': su, 'v_vaxxed': sv}
            json_obj = json.dumps(ob)
            fvc.write(json_obj+'\n')
        fp.close()
        fg.close()
        fvc.close()
    
    fPGraph = open("images/vax_graphP.json", "w")
    for u,v in P.edges():
        col = P[u][v]['color']
        w = P[u][v]['weight']
        pubu = P.nodes[u]['data'].public_dest
        pubv = P.nodes[v]['data'].public_dest
        c = p[u][v]['contacts']
        ob = {'u': u, 'v': v, 'weight': w, 'color':col, 'u_public': pubu, 'v_public': pubv, 'contacts': c}
        json_obj = json.dumps(ob)
        fPGraph.write(json_obj+'\n')
        
    fGraph = open("images/vax_graphG.json", "w")
    for u,v in G.edges():
        su = str(G.nodes[u]['data'].state)
        sv = str(G.nodes[v]['data'].state)
        ob = {'u': u, 'v': v, 'u_state': su, 'v_state': sv}
        json_obj = json.dumps(ob)
        fGraph.write(json_obj+'\n')
    
    fVCGraph = open("images/vax_graphVC.json", "w")
    for u,v in VC.edges():
        su = VC.nodes[u]['data'].is_vaccinated
        sv = VC.nodes[v]['data'].is_vaccinated
        thshld = VC.nodes[v]['t']
        ob = {'u': u, 'v': v, 'u_vaxxed': su, 'v_vaxxed': sv, 't': thshld}
        json_obj = json.dumps(ob)
        fVCGraph.write(json_obj+'\n')
    fPGraph.close()
    fGraph.close()
    fVCGraph.close()

def percent_infected():
    print('HOMES:')
    home_nodes = get_homes()
    for h in home_nodes:
        home_str = ''
        infected = 0
        for n in h:
            was_infected = (n.state == State.RECOVERED)
            if was_infected:
                home_str += (str(n.id) + '+ ')
                infected += 1
            else:
                home_str += (str(n.id) + '- ')
        print(home_str + '| ' + str(infected) + '/' + str(len(h)))
    
def get_homes():
    nodes_per_home = []
    for h in homes:
        home_nodes = []
        for n in P.nodes:
            n = P.nodes[n]['data']
            if n.home == h:
                home_nodes.append(n)
        nodes_per_home.append(home_nodes)
    return nodes_per_home

    

# def avg_clustering(a):
#     i = 0
#     c = 0
#     for n in a:
#         n = n[0]
#         i += 1
#         c += n
#     if i == 0:
#         return -1
#     return round(c/i,4)

# def avg_degree(a):
#     i = 0
#     d = 0
#     for n in a:
#         n = n[1]
#         if n < 0:
#             continue
#         i += 1
#         d += n
#     if i == 0:
#         return -1
#     return round(d/i,4)


# def draw_G():
#     color_map = []
#     for node in G:       
#         node = G.nodes[node]['data']
#         if node.vulnerability == Vulnerability.HIGH:
#             color_map.append('orange')
#         elif node.vulnerability == Vulnerability.MEDIUM:
#             color_map.append('#0080FF')
#         else:
#             color_map.append('green')
#     pos = graphviz_layout(G, prog="twopi")
#     plt.figure(figsize=(10,10))
#     nx.draw(G,pos, node_color=color_map, with_labels = True)
#     # nx.draw(G, node_color=color_map, with_labels = True)
#     plt.savefig("images/propagation.png")
#     plt.show()

# def draw_P():
#     color_map = []
#     color_options = ['#FF0000','#FF9999','#FF8000','#FFFF00','#80FF00','#009900','#66FFB2','#009999','#00FFFF','#004C99',
#               '#66B2FF','#9999FF','#0000CC','#7F00FF','#FF00FF','#CC0066','#C0C0C0','#606060','#336600','#999900',
#               '#CCCCFF','#CCFFFF','#FFCCFF','#666600']
#     for node in P:       
#         node = P.nodes[node]['data']
#         nid = node.id
#         mod = nid % 24
# #         color_map.append(1000*mod)
#         color_map.append(color_options[mod])
# #         if node.vulnerability == Vulnerability.HIGH:
# #             color_map.append('orange')
# #         elif node.vulnerability == Vulnerability.MEDIUM:
# #             color_map.append('#0080FF')
# #         else:
# #             color_map.append('green')
#     colors = [P[u][v]['color'] for u,v in P.edges()]
#     plt.figure(figsize=(12,12))
#     pos = graphviz_layout(P, prog="fdp")
#     nx.draw(P,pos, node_color=color_map, edge_color=colors, with_labels = True)
#     plt.savefig("images/proximity.png")
#     plt.show()

# def draw_VC(graph):
#     color_map = []
#     color_options = ['#FF0000','#FF9999','#FF8000','#FFFF00','#80FF00','#009900','#66FFB2','#009999','#00FFFF','#004C99',
#               '#66B2FF','#9999FF','#0000CC','#7F00FF','#FF00FF','#CC0066','#C0C0C0','#606060','#336600','#999900',
#               '#CCCCFF','#CCFFFF','#FFCCFF','#666600']
#     for node in graph:       
#         if graph.nodes[node]['data'].is_vaccinated:
#             color_map.append('#209E2E') #green
#         else:    
#             color_map.append('#B3B3B3') #grey
# #     colors = [graph[u][v]['color'] for u,v in graph.edges()]
#     plt.figure(figsize=(8,8))
#     pos = graphviz_layout(graph, prog="fdp")
# #     nx.draw(graph,pos, node_color=color_map, edge_color=colors, with_labels = True)
#     nx.draw(graph,pos, node_color=color_map, with_labels = True)
#     plt.show()
#     plt.clf()

def get_R0():
    ln = 0 
    e = 0
    ni = 0
    for n in G.nodes:
        if float(G.nodes[n]['data'].days_infected/G.nodes[n]['data'].recovery_time)<0.5 and G.nodes[n]['data'].state == State.INFECTIOUS:
            ni+=1
            ln+=1
#         else:
        elif G.nodes[n]['data'].state == State.INFECTIOUS:
            ni+=1
            e += G.out_degree(n)
    if ((ni - ln)) ==0:
        return 0
    return e/(ni - ln)

# def clustering_degree():
#     h = []
#     m = []
#     l = []
#     cluster = nx.clustering(P)
# #     print(cluster)
#     for node in P:       
#         node = P.nodes[node]['data']
#         c = cluster[node.id]
#         d = -1
#         try:
#             d = G.out_degree(node.id)
#         except:
#             d = -1

#         if node.vulnerability == Vulnerability.HIGH:
#             h.append((c,d))
#         elif node.vulnerability == Vulnerability.MEDIUM:
#             m.append((c,d))
#         else:
#             l.append((c,d))
#     print('High Vulnerability Proximity Clustering & Propagation Degree:')
#     for n in h:
#         print('clustering: ' + str(n[0]) + ' | degree: ' + str(n[1]))
#     print('Medium Vulnerability Proximity Clustering & Propagation Degree:')
#     for n in m:
#         print('clustering: ' + str(n[0]) + ' | degree: ' + str(n[1]))
#     print('Low Vulnerability Proximity Clustering & Propagation Degree:')
#     for n in l:
#         print('clustering: ' + str(n[0]) + ' | degree: ' + str(n[1]))
#     return {'h':h,'m':m,'l':l}

# def print_vulnerabilities(G):
#     h = 0
#     m = 0
#     l=0

#     for n in G:
# #         print(G.nodes[n]['data'].vulnerability)
#         if G.nodes[n]['data'].vulnerability == Vulnerability.HIGH:
#             h += 1
#         elif G.nodes[n]['data'].vulnerability == Vulnerability.MEDIUM:
#             m+= 1
#         else:
#             l += 1
#     g_name = ' for infected nodes:'
#     if G.name == 'P':
#         g_name = ' for all nodes in model: '
#     print('Vulnerabilities' + g_name)
#     print('number of high vulnerability nodes: ' + str(h))
#     print('number of medium vulnerability nodes: ' + str(m))
#     print('number of low vulnerability nodes: ' + str(l))
#     print('\n')
    

# def draw_P2(P2):
#     color_map = []
#     color_options = ['#FF0000','#FF9999','#FF8000','#FFFF00','#80FF00','#009900','#66FFB2','#009999','#00FFFF','#004C99',
#               '#66B2FF','#9999FF','#0000CC','#7F00FF','#FF00FF','#CC0066','#C0C0C0','#606060','#336600','#999900',
#               '#CCCCFF','#CCFFFF','#FFCCFF','#666600']
#     for node in P:       
#         node = P.nodes[node]['data']
#         nid = node.id
#         mod = nid % 24
#         color_map.append(color_options[mod])
        
#     colors = [P[u][v]['color'] for u,v in P.edges()]
#     plt.figure(figsize=(12,12))
#     pos = graphviz_layout(P, prog="fdp")
#     nx.draw(P,pos, node_color=color_map, edge_color=colors, with_labels = True)
#     plt.show()
    
    


    
# if __name__ == "__main__":
#     main()
main()

