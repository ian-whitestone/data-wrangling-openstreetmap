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

* size of the file
  + toronto_map.osm --> 99 MB
  + toronto.db      --> 55 MB

## Number of Unique Users

`
sqlite> SELECT count(distinct uid) FROM (SELECT uid FROM nodes UNION ALL SELECT uid FROM ways) a;

`

`770`

## Top 10 Contributing Users


## Number of Nodes

`                     
sqlite> select count(id) from nodes;

`

388107

## Number of Ways

`
sqlite> select count(id) from ways;

`

72454

* number of chosen type of nodes, like cafes, shops etc.

## Conclusion
