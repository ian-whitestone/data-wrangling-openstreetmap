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

After storing the un-cleaned data in a sqlite database, it was explored and audited for quality and completeness. Four main problems were identified with the data. Each one is explored in more detail below.

1) Problematic Characters

2) Street Names

3) Postal Codes

4) Cities & Provinces

### Problematic Characters

Certain tags were found to contain problematic characters. These characters can result in messy values that are either hard to read or process programatically. In order to exclude such tags from the dataset, a python regular expression was used.

`re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')`

The actual regular expression `[=\+/&<>;\'"\?%#$@\,\. \t\r\n]` looks for new lines, tabs, commas, single/double quotes, semi-colons, equal signs or characters like %,?,%,$,@,#. If any of these characters are found in the tags key, it is not included. An example of a problematic string is from the tag shown below, with a period in 'just-eat.ca'.

{'v': 'yes', 'k': 'just-eat.ca'}

### Street Names
Using a list of expected street names (i.e. "Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road"), the street names present in the Toronto OSM data were audited for irregularities. The [audit.py](https://github.com/ian-whitestone/data-wrangling-openstreetmap/blob/master/audit.py) script was used to identify street names that did not contain these expected values.

An iterative process was performed where additional street names were added to the list of expected names. Other common names not included in the original list were "Crescent","Close","Way","Terrace". In Toronto, many streets are identified by their quadrant in the city. For example, Queen Street will either appear as Queen Street West or Queen Street East. As a result, the key words "East","West","North","South" were also added to the list of expected street names.

Another interesting quirk in the data was the inclusion of city parks as streets. For example, Trinity Bellwoods Park was tagged as a street name, despite their being no such street in Toronto.

After this process was completed, a final list of problematic names were identified and a dictionary was created for cleaning.

```javascript
{ "St": "Street","St.": "Street","Blvd": "Boulevard","Ave": "Avenue","Ave.": "Avenue","Rd": "Road","STREET": "Street","avenue": "Avenue","street": "Street","E": "East","W": "West"}
```

Two python functions were created to identify bad street names and update them accordingly.

```python
def clean_postal(postal_code):
    """
    removes whitespaces from postal code, ensure it is the correct length and format
    <postal_code> postal code in the raw format
    """
    char_type = {1:0,2:1,3:0,4:1,5:0,6:1} ##1 if integer, 0 if alphabetical

    postal_code = "".join(postal_code.split()) ##remove all spaces
    postal_code = postal_code.upper() ##convert to upper case

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

def clean_street(street_name,expected=EXPECTED_STREETS,street_type_re=STREET_TYPE_RE):
    """
    searches street name for expected key words, if missing, passes street name into update_street_name()
    <street name> name of street
    <expected> list of expected street names/key words
    <street_type_re> regular expression used to search the street name
    """
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            return update_street_name(street_name)
        else:
            return street_name

    return street_name
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

```
num_chars,count
7,760
6,32
8,8
3,1
16,1
```

In Canada, postal codes are 6 unique characters, and are commonly formatted as "A1A 1A1" or "A1A1A1". As a result, both 6 and 7 character length strings are expected. The query above returned some postal codes that were 8,3 and 16 characters long.

The 8 character postal codes were due to trailing spaces (ex. "M4X 1P3‬ ").
The 16 character postal code actually contained 2 postal codes "M5T 1R9, M1P 2L7".

The easiest solution is to use the Python `split()` function to remove all spaces from the postal codes. The 3 character and 16 characters postal codes cannot be cleaned in any way, so they should be ignored.

Using the known format of the Canadian postal code, the strings are further audited.

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

As expected, only integers are present, with the exception of one 'G'. This was actually the result of an incomplete postal code "M5J 2G".

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

As expected, only letters were present, with the exception of one '2' from the postal code "M5J 2G". Some lower case letters are present which should be converted.

The first character of a postal code represents a large area in the city.

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

```
postal_char,count
K,1
M,1395
m,1
```

With the exception of one postal code, all codes start with "M" as expected. The postal code starting with "K" is actually from Orleans, Ontario, a city near Ottawa, Ontario. This was clearly a mistake as the user was attempting to enter the postal code for 398 Palmerston Boulevard, a valid address in Toronto.
```
368947582,city,Toronto,addr
368947582,housenumber,398,addr
368947582,postcode,"K4A 1W9",addr
368947582,province,Ontario,addr
368947582,street,"Palmerston Boulevard",addr
368947582,landuse,residential,regular
```

A function was created to clean the postal codes based on the results found above.

```python
def clean_postal(postal_code):
    """
    removes whitespaces from postal code, convert to upper case, ensure it is the correct length and format
    <postal_code> postal code in the raw format
    """
    char_type = {1:0,2:1,3:0,4:1,5:0,6:1} ##1 if integer, 0 if alphabetical

    postal_code="".join(postal_code.split()) ##remove all spaces
    postal_code = postal_code.upper() ##convert to upper case

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

###validate the function is working as expected
>>> print (clean_postal('M9Z 1D5'))
M9Z1D5
>>> print (clean_postal('M9Z 1D'))
None
>>> print (clean_postal('M9Z1DF'))
None
```

### Cities & Provinces

The main city and province in the dataset should be Toronto, Ontario.

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

As shown above, there is clearly some inconsistent naming of the same city/province, with names like "City of Toronto","toronto","Toronto","on" etc. Some spelling mistakes are also present.

York, North York and East York are all former municipalities or districts within the current city of Toronto. It is up to debate whether these should be tagged at "cities".

Don Mills is not a city, and to some people's surprise, neither is "Torontoitialian".


## Data Overview

With the cleaned dataset, a final set of queries were performed to explore the data.

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

### Most Common Way Tags
```sql
SELECT key,count(*)
FROM ways_tags
GROUP BY 1
ORDER BY count(*) DESC
LIMIT 10;
```

```
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
```

### Most Common Node Tags
```sql
SELECT key,count(*)
FROM nodes_tags
GROUP BY 1
ORDER BY count(*) DESC
LIMIT 10;
```

```
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
```

### Most Common Amenities

```sql
SELECT value,count(*)
FROM nodes_tags
WHERE key='amenity'
GROUP BY 1
ORDER BY count(*) DESC
LIMIT 20;

```

```
restaurant,919
fast_food,844
bench,788
cafe,553
post_box,550
parking,450
bicycle_parking,329
waste_basket,307
bank,278
vending_machine,235
waste_basket;recycling,233
telephone,223
recycling,186
pharmacy,177
pub,152
bicycle_rental,124
relay_box,122
dentist,121
car_sharing,91
place_of_worship,91
```

## Conclusion

It is clear that a significant effort has been undertaken by various users to contribute data to the Toronto OSM area. To ensure accurate data is entered, I believe OSM should implement some data quality rules that restrict the data that can be entered. For example, they could include postal code rules (i.e. number of characters, character format (integer vs. alphabetical charactr at certain positions)) based on the known postal format of the country. With cities and provinces, similar rules/restrictions could be put in place to ensure that users enter cities/provinces that actually exist. This could easily be checked against a database of existing cities and provinces for each country.

Some anticipated problems with implementing such changes would be rules that are too restrictive and end up blocking valid values. Additionally, such rules could discourage users from contributing data due to the added difficulty.

For future work, it is recommended to implement more regular expressions to perform the data validation and cleaning, rather than the hard-coded values/logic that were used in mapParser.py.
