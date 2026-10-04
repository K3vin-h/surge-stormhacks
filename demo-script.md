# Demo video script

“Our app uses sensor readings to show regional risk and help find routes to possible evacuation destinations.

Each region has three readings stored in a JSON file: rainfall over the past 24 hours, river level compared with its warning level, and soil moisture.

We combine these readings into a score, giving rainfall and river level the most weight. That score assigns a category from Low to Extreme. Within the assessed area, we also check the mapped hazard zones and use whichever risk is higher. Missing readings appear as Unknown. For this demo, the readings are simulated.

For routing, we turn mapped roads into a network and remove connections that cross the hazard footprint, are closed, or aren’t allowed for the selected travel mode.

Starting from a village or GPS location, the app searches for the shortest road paths to destinations in Low-risk areas. It lists the closest reachable options within the distance limit, or picks the closest option in resident mode.

The sensor score helps decide which destinations qualify; road restrictions decide which paths are available. These are demo candidates that still require verification before real-world use.”
