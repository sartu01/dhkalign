# --- build stage ---
FROM golang:1.22-alpine AS build
WORKDIR /src

# Cache deps first
COPY go.mod go.sum* ./
RUN go mod download

# Source
COPY . .

# Optional build metadata (passed by CI/Fly as --build-arg; defaults are safe)
ARG COMMIT_SHA=dev
ARG BUILD_TIME=

# Static, small binary
ENV CGO_ENABLED=0
RUN go build -trimpath -ldflags="-s -w" -o /out/server

# --- runtime stage ---
FROM gcr.io/distroless/static-debian12

# Port & metadata for /go/version
ARG COMMIT_SHA=dev
ARG BUILD_TIME=
ENV PORT=8080 \
    COMMIT_SHA=${COMMIT_SHA} \
    BUILD_TIME=${BUILD_TIME}

EXPOSE 8080
COPY --from=build /out/server /server
USER nonroot:nonroot
ENTRYPOINT ["/server"]
