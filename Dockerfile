# Use a base image with Go installed (Alpine is lightweight)
FROM golang:1.23-bookworm

# Install necessary packages: Chromium and other utilities
RUN apt update && apt install -y \
    chromium \
    python3 \
    python3-pip \
    && go install github.com/sensepost/gowitness@latest

# Set environment variable for Chromium path
ENV GOWITNESS_BROWSER_PATH=/usr/bin/chromium-browser
RUN pip install b-hunters==1.1.4 --break-system-packages
# Set up GoWitness entry point to simplify usage
# ENTRYPOINT ["gowitness"]
WORKDIR /app/service/
COPY gowitnessm gowitnessm
# Default command to help with usage
CMD ["python3","-m","gowitnessm"]