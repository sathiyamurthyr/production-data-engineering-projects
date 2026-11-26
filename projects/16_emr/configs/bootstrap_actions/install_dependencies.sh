#!/bin/bash
# ==============================================================================
# Script Name: install_dependencies.sh
# Description: EMR Bootstrap Action script to install Python dependencies,
#              system packages, and configure runtime environments.
# Author: Sathiya Murthy (Data Engineering Diaries)
# ==============================================================================

set -euo pipefail

# Redirect stdout and stderr to a log file for CloudWatch / S3 debugging
LOG_FILE="/var/log/emr_bootstrap_install.log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "========================================================="
echo "EMR Bootstrap Action Started: $(date)"
echo "========================================================="

# Detect node type (Primary, Core, or Task)
IS_MASTER=false
if [ -f /mnt/var/lib/info/instance.json ]; then
    IS_MASTER=$(jq -r '.isMaster' /mnt/var/lib/info/instance.json)
fi

echo "Node status - Is Master Node: ${IS_MASTER}"

# Update package repository and install basic system utilities
echo "Updating system packages..."
sudo yum update -y --security
sudo yum install -y htop git gcc openssl-devel bzip2-devel libffi-devel python3-devel

# Install python libraries required for PySpark ETL and Machine Learning
echo "Installing Python dependencies via pip..."
# Ensure pip is upgraded
sudo python3 -m pip install --upgrade pip

# Install specific Python libraries commonly needed for custom Spark UDFs and ETL steps
# Note: we use standard numpy/pandas/boto3/requests/cryptography versions
sudo python3 -m pip install \
    boto3==1.28.0 \
    pandas==1.5.3 \
    numpy==1.23.5 \
    pyarrow==11.0.0 \
    scikit-learn==1.2.2 \
    requests==2.31.0 \
    cryptography==41.0.1

echo "Python packages installed successfully:"
python3 -m pip list | grep -E "boto3|pandas|numpy|pyarrow|scikit-learn|requests"

# master-specific setup (e.g. download external jars, configs)
if [ "${IS_MASTER}" = "true" ]; then
    echo "Running Master-Node specific configurations..."
    # E.g. download third-party connectors or setup shared configuration files
    # sudo wget -P /usr/lib/spark/jars/ https://repo1.maven.org/maven2/org/apache/spark/spark-avro_2.12/3.3.0/spark-avro_2.12-3.3.0.jar
fi

echo "========================================================="
echo "EMR Bootstrap Action Completed Successfully: $(date)"
echo "========================================================="
exit 0
