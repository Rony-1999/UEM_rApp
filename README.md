# UEM_rApp

Assuming that all the libraries are already installed into the system.

Required lIbraries:

-Flask version 2.2.2

-python version 3.8

### Assuming pynTs or gNB is pushing no. of UEs counters to influxDB 

pynTs : https://github.com/o-ran-sc/sim-o1-ofhmp-interfaces

### GET metrics from URL : HOST_IP:5002/metircs

### How to run rApp

```
# Bring up rApp
python3 UE_MANAGER_RAPP.py

```

### Successfully Created Policies can be seen at URL : HOST_IP:5002/policies/view


```
# Bring up mock xApp
python3 load_balancing_xapp.py

```
