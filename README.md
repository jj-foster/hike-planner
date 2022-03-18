# Hike Time Calculator
Maps GPS file &amp; calculates walking distance and time. Hike can be segmented by painting over path with different days.

Accurately planning a hike/trek can be difficult - a big reason is that timings are vague. A one speed fits all approach is too conservative and is not appropriate when traversing mountainous or other difficult terrain. To combat this, I collected pace data from strava for different terrain gradients and compiled a dataset of my walking speeds. This is what drives the calculator.

The UI accepts a gps path file input (gpx, kml/kmz) and plots this on a map, for which tiles are downloaded from openstreetmaps. Altitudes along the path are downloaded from opentopodata and are used to plot the elevation profile, which is combined with the calculated walking speeds. Some smoothing is applied to the speed datapoints to account for unrealistic sudden jumps in terrain gradient (opentopodata is only available for 30m resolution).
A paint function is implemented so the path can be easily segmented into different days - each day has the total walking distance and time calculated.

![screenshot](https://user-images.githubusercontent.com/79290428/159019702-3fd23779-31c4-4a3d-96ea-2eed84bd637f.png)

### Installation
1. Install python (tested on 3.9.5)
2. Install packages in requirements.txt
   >pip install -r requirements.txt
3. Run hike_data_GUI.py from console. For help:
   >py ./hike_data_GUI.py -h

### Features
- Plots hike path on topographical map.
- Allows for switching/inputting other map servers.
- Allows map zoom level adjustment.
- Plots elevation profile and calculated walking speed along path distance.
- Enables segmentation of hike by painting days on map.
- Dynamically updates paint colours based on number of days.
- Customise rest times.
- Calculate day stats including distance walked and total duration.

### More info
- Map tile servers: https://wiki.openstreetmap.org/wiki/Tile_servers
- Opentopodata: https://www.opentopodata.org/
