# Use a base image with Go installed (Alpine is lightweight)
FROM golang:1.26-bookworm

# Install necessary packages: Chromium and other utilities
RUN apt update && apt install -y \
    chromium \
    python3 \
    python3-pip \
    && go install github.com/sensepost/gowitness@latest

# Set environment variable for Chromium path
ENV GOWITNESS_BROWSER_PATH=/usr/bin/chromium-browser
# The shared class is built from this repository, not from the published
# release: a worker that calls auth_headers(task) against a release that
# does not have it fails inside the scan.  scripts/build_workers.sh passes
# the local wheel; the default is the published release.
ARG B_HUNTERS_WHEEL=b-hunters==1.2.0
RUN pip install ${B_HUNTERS_WHEEL} --break-system-packages
# Set up GoWitness entry point to simplify usage
# ENTRYPOINT ["gowitness"]
WORKDIR /app/service/
COPY gowitnessm gowitnessm
# Default command to help with usage
CMD ["python3","-m","gowitnessm"]