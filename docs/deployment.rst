Deployment Guide
================

This guide covers different deployment scenarios for the Plugin Adapter service, from development to production environments.

Docker Deployment
-----------------

Docker is the recommended deployment method for all environments.

Basic Docker Deployment
~~~~~~~~~~~~~~~~~~~~~~~

Run a single instance:

.. code-block:: bash

   docker run -d \
     --name plugin-adapter \
     -e UTXO_PLUGIN_LIST='BLOCK:172.31.8.23,SYS:172.31.10.15' \
     -p 5000:5000 \
     blocknetdx/plugin-adapter

With custom port:

.. code-block:: bash

   docker run -d \
     --name plugin-adapter \
     -e UTXO_PLUGIN_LIST='BLOCK:172.31.8.23,SYS:172.31.10.15' \
     -p 8080:5000 \
     blocknetdx/plugin-adapter

Docker Compose
~~~~~~~~~~~~~~

For multi-service deployments, use Docker Compose:

.. code-block:: yaml

   version: '3.8'
   services:
     plugin-adapter:
       image: blocknetdx/plugin-adapter:latest
       container_name: plugin-adapter
       restart: unless-stopped
       ports:
         - "5000:5000"
       environment:
         UTXO_PLUGIN_LIST: 'BLOCK:electrumx-block,SYS:electrumx-sys'
       depends_on:
         - electrumx-block
         - electrumx-sys
       networks:
         - crypto-network

     electrumx-block:
       image: electrumx:latest
       # ... ElectrumX configuration

     electrumx-sys:
       image: electrumx:latest
       # ... ElectrumX configuration

   networks:
     crypto-network:
       driver: bridge

Kubernetes Deployment
---------------------

Production Kubernetes deployment with high availability.

Basic Deployment
~~~~~~~~~~~~~~~~

.. code-block:: yaml

   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: plugin-adapter
     namespace: crypto-services
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: plugin-adapter
     template:
       metadata:
         labels:
           app: plugin-adapter
       spec:
         containers:
         - name: plugin-adapter
           image: blocknetdx/plugin-adapter:latest
           ports:
           - containerPort: 5000
           env:
           - name: UTXO_PLUGIN_LIST
             value: "BLOCK:10.0.1.10,SYS:10.0.1.11"
           resources:
             requests:
               memory: "256Mi"
               cpu: "100m"
             limits:
               memory: "512Mi"
               cpu: "200m"
           livenessProbe:
             httpGet:
               path: /height
               port: 5000
             initialDelaySeconds: 30
             periodSeconds: 10
           readinessProbe:
             httpGet:
               path: /height
               port: 5000
             initialDelaySeconds: 5
             periodSeconds: 5

Service
~~~~~~~

.. code-block:: yaml

   apiVersion: v1
   kind: Service
   metadata:
     name: plugin-adapter-service
     namespace: crypto-services
   spec:
     selector:
       app: plugin-adapter
     ports:
     - protocol: TCP
       port: 5000
       targetPort: 5000
     type: ClusterIP

Ingress
~~~~~~~

.. code-block:: yaml

   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: plugin-adapter-ingress
     namespace: crypto-services
     annotations:
       kubernetes.io/ingress.class: "nginx"
       nginx.ingress.kubernetes.io/enable-cors: "true"
       nginx.ingress.kubernetes.io/cors-allow-origin: "https://your-app.com"
   spec:
     rules:
     - host: api.your-app.com
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: plugin-adapter-service
               port:
                 number: 5000

ConfigMap and Secrets
~~~~~~~~~~~~~~~~~~~~~

Store configuration in Kubernetes ConfigMap:

.. code-block:: yaml

   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: plugin-adapter-config
     namespace: crypto-services
   data:
     UTXO_PLUGIN_LIST: "BLOCK:10.0.1.10,SYS:10.0.1.11,BTC:10.0.1.12"

Use the ConfigMap in deployment:

.. code-block:: yaml

   env:
   - name: UTXO_PLUGIN_LIST
     valueFrom:
       configMapKeyRef:
         name: plugin-adapter-config
         key: UTXO_PLUGIN_LIST

Monitoring and Observability
-----------------------------

Health Checks
~~~~~~~~~~~~~

The service provides built-in health check endpoints:

* ``GET /height`` - Returns block heights for all configured currencies
* ``POST /`` with ``{"method": "ping"}`` - Simple connectivity check

Configure these as liveness and readiness probes in your deployment.

Logging
~~~~~~~

The service logs to both stdout and debug.log file:

.. code-block:: bash

   # View logs from Docker
   docker logs plugin-adapter

   # View logs from Kubernetes
   kubectl logs -f deployment/plugin-adapter -n crypto-services

Log levels:

* ``DEBUG`` - Detailed request/response information
* ``INFO`` - General operation information
* ``WARNING`` - Configuration or connection warnings
* ``ERROR`` - Errors and exceptions

Metrics
~~~~~~~

Monitor these key metrics:

* Request rate and response times
* Error rates by currency and method
* Connection status to ElectrumX servers
* Memory and CPU usage

Security Considerations
-----------------------

Network Security
~~~~~~~~~~~~~~~~

* Use TLS/SSL for production deployments
* Restrict access to the API port (5000) using firewalls
* Consider using a reverse proxy with authentication

Container Security
~~~~~~~~~~~~~~~~~~

* Run containers as non-root user (planned enhancement)
* Keep base images updated
* Use image scanning tools

Environment Variables
~~~~~~~~~~~~~~~~~~~~

* Store sensitive configuration in Kubernetes secrets
* Avoid logging sensitive information

Scaling Strategies
------------------

Horizontal Scaling
~~~~~~~~~~~~~~~~~~

Scale by adding more replicas:

.. code-block:: bash

   kubectl scale deployment/plugin-adapter --replicas=5 -n crypto-services

Ensure your ElectrumX servers can handle the increased load.

Load Balancing
~~~~~~~~~~~~~~

Use a load balancer in front of multiple Plugin Adapter instances:

.. code-block:: yaml

   spec:
     type: LoadBalancer
     ports:
     - port: 5000
       targetPort: 5000
     selector:
       app: plugin-adapter

Caching Strategy
~~~~~~~~~~~~~~~~

Consider implementing caching for frequently requested data:

* Block heights (cache for 10-30 seconds)
* Transaction data (cache for 60 seconds)
* Balance queries (cache for 5-10 seconds)

Backup and Recovery
-------------------

Configuration Backup
~~~~~~~~~~~~~~~~~~~~

Backup your configuration regularly:

.. code-block:: bash

   # Export ConfigMap
   kubectl get configmap plugin-adapter-config -n crypto-services -o yaml > config-backup.yaml

   # Export deployment configuration
   kubectl get deployment plugin-adapter -n crypto-services -o yaml > deployment-backup.yaml

Disaster Recovery
~~~~~~~~~~~~~~~~~

For high availability deployments:

1. **Multi-region deployment**: Deploy to multiple regions
2. **Data replication**: Ensure ElectrumX data is replicated
3. **Automated failover**: Use DNS-based failover solutions

Performance Tuning
------------------

Connection Pooling
~~~~~~~~~~~~~~~~~~

The service automatically manages connections to ElectrumX servers. For optimal performance:

* Ensure sufficient network bandwidth
* Monitor connection pool utilization
* Configure appropriate timeouts

Resource Allocation
~~~~~~~~~~~~~~~~~~

Recommended resource limits:

.. code-block:: yaml

   resources:
     requests:
       memory: "256Mi"
       cpu: "100m"
     limits:
       memory: "512Mi"
       cpu: "200m"

For high-traffic deployments, increase limits based on monitoring data.

Troubleshooting Deployment Issues
---------------------------------

Service won't start
~~~~~~~~~~~~~~~~~~~

Check the logs for configuration errors:

.. code-block:: bash

   kubectl logs deployment/plugin-adapter -n crypto-services

Common issues:

* Missing ``UTXO_PLUGIN_LIST`` environment variable
* Invalid currency symbols
* Network connectivity to ElectrumX servers

High resource usage
~~~~~~~~~~~~~~~~~~~

Monitor resource usage:

.. code-block:: bash

   kubectl top pods -l app=plugin-adapter -n crypto-services

Consider scaling horizontally or increasing resource limits.

Connection timeouts
~~~~~~~~~~~~~~~~~~~

If experiencing timeouts to ElectrumX servers:

1. Check network connectivity
2. Verify ElectrumX server status
3. Increase timeout values if needed
4. Consider adding more ElectrumX servers

For additional troubleshooting help, see the :doc:`troubleshooting` guide.