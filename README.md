# Hike Time Calculator
Maps GPS file &amp; calculates walking distance and time. Hike can be segmented by painting over path with different days.

Accurately planning a hike/trek can be difficult - a big reason is that timings are vague. A one speed fits all approach is too conservative and is not appropriate when traversing mountainous or other difficult terrain. To combat this, I collected pace data from strava for different terrain gradients and compiled a dataset of my walking speeds. This is what drives the calculator.

The UI accepts a gps path file input (gpx, kml/kmz) and plots this on a map, for which tiles are downloaded from openstreetmaps. Altitudes along the path are downloaded from opentopodata and is used to plot the elevation profile along with the calculated walking speeds.
A paint function is implemented so the path can be easily segmented into different days - each day has the total walking distance and time calculated.

![screenshot](https://user-images.githubusercontent.com/79290428/157776701-76731c42-f395-44a4-b549-1a682448f0b6.png)

### Installation
1. Install python 3.9
2. Install packages in requirements.txt
3. Run hike_data_GUI.py

##### More info
- Map tile servers: https://wiki.openstreetmap.org/wiki/Tile_servers
- Opentopodata: https://www.opentopodata.org/
