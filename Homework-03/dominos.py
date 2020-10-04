# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 15:24:09 2019

@author: vkaus
"""

import sqlite3
import pandas as pd
from haversine import haversine,Unit

conn=sqlite3.connect('Dominos.db')
cursor=conn.cursor()

cursor.execute('create table if not exists Distributor_data(Distri_Center_ids text,address text,latitude_dis real,longitude_dis real,supply_capacity float,cost float)')
distributor_data=[]
distributor_data=pd.read_csv(r'Distributor_Data.csv')
distributor_data = distributor_data.values.tolist()
cursor.executemany('INSERT INTO Distributor_data VALUES(?,?,?,?,?,?)', distributor_data)
rowsA=cursor.fetchall()

cursor.execute('create table if not exists Daily_demand(Date date,store_number integer,pizza_sales integer)')
daily_demand=[]
daily_demand=pd.read_csv(r'OR 604 Dominos Daily Demand.csv')
daily_demand = daily_demand.values.tolist()
cursor.executemany('INSERT INTO Daily_demand VALUES(?,?,?)', daily_demand)
rowsB=cursor.fetchall()

cursor.execute('create table if not exists Good_Dominos_data(store_number integer,store text,street text,city text,state text,zip text,latitude_st real,longitude_st real)')
dominos_data=[]
dominos_data=pd.read_csv(r'OR604 Good Dominos Data.csv')
dominos_data = dominos_data.values.tolist()
cursor.executemany('INSERT INTO Good_Dominos_data VALUES(?,?,?,?,?,?,?,?)', dominos_data)
rowsC=cursor.fetchall()

cursor.execute('select Distributor_data.Distri_Center_ids,Good_Dominos_data.store_number,latitude_dis,longitude_dis,latitude_st,longitude_st from  Distributor_data cross join Good_Dominos_data')
rows_lat_lon=cursor.fetchall()
distance=dict()
for center,store,dis_lat,dis_long,st_lat,st_long in rows_lat_lon:
    distance[center.replace(' ','_'),store]=haversine((dis_lat,dis_long),(st_lat,st_long),unit=Unit.MILES)

cursor.execute('select store_number,avg(pizza_sales)*7 from Daily_demand GROUP by store_number')
rows_demand=cursor.fetchall()
demand=dict(rows_demand)

cursor.execute('select Distri_Center_ids,cost from Distributor_data')
rows_cost=cursor.fetchall()
Cost=dict()
for center,cost in rows_cost:
    Cost[center.replace(' ','_')]=cost

cursor.execute('select Distri_Center_ids,supply_capacity from Distributor_data')
rows_supply=cursor.fetchall()
Supply=dict()
for center,supply in rows_supply:
    Supply[center.replace(' ','_')]=int(supply.replace(',',''))

    
conn.commit()
conn.close()


abc={}
abc['demand'] = demand
abc['Cost'] = Cost
abc['Supply']= Supply
abc['distance']=distance

abc


dominos_data=pd.DataFrame(dominos_data)
stores_demand=set(abc['demand'].keys())
new_store= set(dominos_data[0]) - stores_demand
closed_store=stores_demand - set(dominos_data[0])
len(new_store)
len(closed_store)

print('Total stores:', len(abc['demand'].keys()))
print('Total good_stores:', len(set(dominos_data[0])))
print('Total New stores:', len(new_store))
print('Total Closed stores:', len(closed_store))

for st in closed_store:
    abc['demand'].pop(st)
    
    
print('Total stores after deleting closed stores are:', len(abc['demand']))


from gurobipy import *

dominos=Model()
dominos.modelSense = GRB.MINIMIZE
dominos.update()

Distribution_Centers=abc['Cost'].keys()
Stores=abc['demand'].keys()


#Decision Variables

no_of_doughs={}

for d in Distribution_Centers:
    for s in Stores:
        no_of_doughs[d,s]=dominos.addVar(obj=(abc['distance'][d,s]*abc['Cost'][d])*1/9000,vtype=GRB.CONTINUOUS,name=f'{d}_{s}')
        
        

#constraints
my_constr={}      
  
for d in Distribution_Centers:
    cname=f'{d}'
    my_constr[cname]=dominos.addConstr(quicksum(no_of_doughs[d,s] for s in Stores) <= abc['Supply'][d],name=cname)
    


for s in Stores:
    cname=f'{s}'
    my_constr[cname]=dominos.addConstr(quicksum(no_of_doughs[d,s] for d in Distribution_Centers) >= abc['demand'][s],name=cname)
    

dominos.update()
dominos.write('dominos.lp')
dominos.optimize()
dominos.write('dominos.sol')



if dominos.Status == GRB.OPTIMAL:
    conn = sqlite3.connect('Dominos.db')
    cursor=conn.cursor()
    dominos_sol=[]
    for k,v in no_of_doughs.items():
        if v.x >0:
            a=(k[0],k[1], v.x)
            dominos_sol.append(a)

cursor.execute('CREATE TABLE IF NOT EXISTS tbldominos(Distribution_Center text,Store_Number integer,No_of_doughs float)')
cursor.executemany('INSERT INTO tbldominos VALUES(?,?,?)', dominos_sol)
cursor.execute('SELECT * FROM tbldominos')
rows = cursor.fetchall() 
print(rows)
conn.commit()
conn.close()



'''
select Distributor_data.Distri_Center_ids,Good_Dominos_data.store_number,latitude_dis,longitude_dis,latitude_st,longitude_st from  Distributor_data cross join Good_Dominos_data

'''