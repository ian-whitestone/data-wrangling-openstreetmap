# Data Wrangling OpenStreetMap
Udacity Course - Data Wrangling OpenStreetMap Data

## Purpose
This project is part of Udacity's Data Analyst Nanodegree. A xml osm file was downloaded for a selected area from OpenStreetMap (OSM). This report details the data auditing and cleaning performed on the raw dataset. After the data is cleaned, it is transformed and stored in a SQL database with a set [schema](https://github.com/ian-whitestone/datawranglingopenstreetmap/blob/master/toronto_db_schema.sql). With the stored dataset, the data and the chosen area are further explored.

## Map Area

For this project I selected a section of downtown [Toronto, Ontario, Canada](http://www.openstreetmap.org/export#map=13/43.6561/-79.3903).

<p align="center">
  <img src=images/toronto_area.png alt="toronto_area" style="width: 450px;" style="height: 450px;" />
</p>


## Data Auditing
1) problematic characters
(look into regular expression and what it searches for)
575248144 tag {'v': 'yes', 'k': 'just-eat.ca'}

2) street names

3) postal codes

4)

## Data Overview

## File Sizes
```
  toronto_map.osm --> 99 MB
  toronto.db -------> 55 MB

```
## Number of Unique Users

``` sql
sqlite> SELECT count(distinct uid) FROM (SELECT uid FROM nodes UNION ALL SELECT uid FROM ways) a;

```

770

## Top 10 Contributing Users

``` sql
sqlite> SELECT uid,count(*) AS num_contributions
FROM (SELECT uid FROM nodes UNION ALL SELECT uid FROM ways) a
GROUP BY 1
ORDER BY num_contributions DESC
LIMIT 10;

```

```
user,num_contributions
1679,335811
40964,55926
3551880,15019
1060930,6434
1108251,4254
3151933,2915
1964104,2878
19492,2505
30035,2006
158267,1989
```

To appreciate the the difference between the top 10 users, a bar plot is included below.

<p align="center">
  <img src=images/top_10_users.png alt="toronto_area" style="width: 450px;" style="height: 450px;" />
</p>



## Number of Nodes

``` sql  
sqlite> SELECT count(id) FROM nodes;

```

388107

## Number of Ways

``` sql
sqlite> SELECT count(id) FROM ways;

```

72454

* number of chosen type of nodes, like cafes, shops etc.

## Conclusion
