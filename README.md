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

1) Problematic Characters

2) Street Names

3) Postal Codes

4) Cities & Provinces

### Problematic Characters

575248144 tag {'v': 'yes', 'k': 'just-eat.ca'}

`re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')`

The actual regular exprresion `[=\+/&<>;\'"\?%#$@\,\. \t\r\n]` looks for new lines, tabs, commas, single/double quotes, semi-colons, equal signs or characters like %,?,%,$,@,#

### Street Names


- parks under street tags

```python
def clean_street(street_name,expected=EXPECTED_STREETS,street_type_re=STREET_TYPE_RE):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            return update_street_name(street_name)
        else:
            return street_name

    return street_name

def update_street_name(street_name,street_name_mapping=STREET_NAME_MAP):
    street_words = street_name.split()

    updated_street_words=[]
    for w in street_words:
        try:
            w = street_name_mapping[w]
        except:
            pass
        updated_street_words.append(w)

    return " ".join(updated_street_words)
```

### Postal Codes

An easy way to investigate malformed postal codes is to examine the length of the postal code string.

```sql
SELECT length(value), count(*)
FROM nodes_tags
WHERE key='postcode'
GROUP BY 1
ORDER BY count(*) DESC;

```

In Canada, postal codes are 6 unique characters, and are commonly formatted as "A1A 1A1" or "A1A1A1"

```
num_chars,count
7,760
6,32
8,8
3,1
16,1
```

8 chars: trailing space
3602419558,postcode,"M4X 1P3‬ ",addr

16 chars
152659345,postcode,"M5T 1R9, M1P 2L7",addr

Easiest solution is to use the Python `strip()` function to remove all spaces from the postal codes. The 3 character and 16 characters postal codes cannot be cleaned in any way, so they should be ignored.

```sql
--the 2nd, 4th and 6th digits of the postal codes should all be integers.
SELECT postal_char,count(*)
FROM
(
  SELECT substr(value,2,1) AS postal_char FROM nodes_tags WHERE key='postcode' AND length(value) IN (6,7)
  UNION ALL
  SELECT substr(value,-1,1) AS postal_char FROM nodes_tags WHERE key='postcode' AND length(value) IN (6,7)
  UNION ALL
  SELECT substr(value,-3,1) AS postal_char FROM nodes_tags WHERE key='postcode' AND length(value) IN (6,7)
  UNION ALL
  SELECT substr(value,2,1) AS postal_char FROM ways_tags WHERE key='postcode' AND length(value) IN (6,7)
  UNION ALL
  SELECT substr(value,-1,1) AS postal_char FROM ways_tags WHERE key='postcode' AND length(value) IN (6,7)
  UNION ALL
  SELECT substr(value,-3,1) AS postal_char FROM ways_tags WHERE key='postcode' AND length(value) IN (6,7)
)
GROUP BY 1;
```

As expected, only integers are present in these
```
postal_char,count
0,37
1,835
2,603
3,410
4,760
5,739
6,420
7,128
8,102
9,155
G,1
```

146040705,postcode,"M5J 2G",addr

```sql
--the 1st,3rd and 5th digits of the postal code should all be alphabetical characters
SELECT postal_char,count(*)
FROM
(
  SELECT substr(value,1,1) AS postal_char FROM nodes_tags WHERE key='postcode' AND length(value) IN (6,7)
  UNION ALL
  SELECT substr(value,3,1) AS postal_char FROM nodes_tags WHERE key='postcode' AND length(value) IN (6,7)
  UNION ALL
  SELECT substr(value,-2,1) AS postal_char FROM nodes_tags WHERE key='postcode' AND length(value) IN (6,7)
  UNION ALL
  SELECT substr(value,1,1) AS postal_char FROM ways_tags WHERE key='postcode' AND length(value) IN (6,7)
  UNION ALL
  SELECT substr(value,3,1) AS postal_char FROM ways_tags WHERE key='postcode' AND length(value) IN (6,7)
  UNION ALL
  SELECT substr(value,-2,1) AS postal_char FROM ways_tags WHERE key='postcode' AND length(value) IN (6,7)
)
GROUP BY 1;
```


```
postal_char,count
2,1
A,248
B,164
C,165
E,145
G,189
H,120
J,176
K,126
L,133
M,1496
N,100
P,160
R,163
S,168
T,160
V,147
W,74
X,99
Y,85
Z,69
a,1
m,1
x,1
```

```sql
SELECT postal_char,count(*)
FROM
(
  SELECT substr(value,1,1) AS postal_char FROM nodes_tags WHERE key='postcode' AND length(value) IN (6,7)
  UNION ALL
  SELECT substr(value,1,1) AS postal_char FROM ways_tags WHERE key='postcode' AND length(value) IN (6,7)
)
GROUP BY 1;
```


368947582,city,Toronto,addr
368947582,housenumber,398,addr
368947582,postcode,"K4A 1W9",addr
368947582,province,Ontario,addr
368947582,street,"Palmerston Boulevard",addr
368947582,landuse,residential,regular

```python
def clean_postal(postal_code):
    char_type = {1:0,2:1,3:0,4:1,5:0,6:1} ##1 if integer, 0 if alphabetical

    postal_code="".join(postal_code.split()) ##remove all spaces

    if len(postal_code)==6:
        pass
    else:
        return

    for i,s in enumerate(postal_code):
        check = (1 if s.isdigit() else 0)
        if check == char_type[i+1]:
            continue
        else:
            return
    return postal_code


>>> print (clean_postal('M9Z 1D5'))
M9Z1D5
>>> print (clean_postal('M9Z 1D'))
None
>>> print (clean_postal('M9Z1DF'))
None
```

### Cities & Provinces

```sql
SELECT value,count(*)
FROM
(
  SELECT value FROM nodes_tags WHERE key='city' or key='province'
  UNION ALL
  SELECT value FROM ways_tags WHERE key='city' or key='province'
)
GROUP BY 1;
```

```
"City of Toronto",29976
"Don Mills",1
"East York",1215
"North York",457
ON,5918
On,3
Onatrio,1
Ontario,169
Onterio,1
Toronto,7657
"Toronto, ON",1
Torontoitalian,1
York,188
"York, Toronto",1
on,1
ontario,2
```



## Data Overview

### File Sizes
```
  toronto_map.osm --> 99 MB
  toronto.db -------> 55 MB
  nodes.csv --------> 30 MB
  nodes_tags.csv ---> 10 MB
  ways.csv ---------> 4 MB
  ways_nodes.csv ---> 10 MB
  ways_tags.csv ----> 8 MB

```
### Number of Unique Users

``` sql
SELECT count(distinct uid) FROM (SELECT uid FROM nodes UNION ALL SELECT uid FROM ways) a;

```

770

### Top 10 Contributing Users

``` sql
SELECT uid,count(*) AS num_contributions
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



### Number of Nodes

``` sql  
SELECT count(id) FROM nodes;

```

388107

### Number of Ways

``` sql
SELECT count(id) FROM ways;

```

72454

### Most Common Ways Tags

source,40284
highway,24179
interpolation,19612
building,18910
surface,13970
name,12666
lanes,11077
access,6659
service,4118
street,3873

### Most Common Nodes Tags
street,45451
housenumber,45431
source,43160
city,35844
highway,11247
name,10051
amenity,8237
country,5622
created_by,5340
operator,3848

* number of chosen type of nodes, like cafes, shops etc.

## Conclusion


suggestions
- postal code audting while entering (consistent formatting)
- city/province auditing while editing (make sure cities exist, consistent formatting )

Problems with above could be that it's too restrictive and blocks real values, or discourages users to participate..

Use regular expressions for auditing - more robust than hardcoded searches.
