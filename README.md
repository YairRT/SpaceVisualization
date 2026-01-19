# SpaceVisualization

## Overall architecture

- Data: the data comes from CelesTrak API, it comes in TLE format and transformed through the SGP4 model 



## Notes
### TLE format
This format allows use to track orbital motion of elements for a short period of time (less than a week). Due to drag and other orbital factors, the accumulated error beyond a couple of days will position the satellite km away from it's actual position.
### SGP4 moodel
This model helps us convert the TLE format to a orbital tracking systems. Inputs: TLE and time diff. since epoch. Outpus: position and velocity vecto with ECI coordinates (Earth-Centered Inertial)
