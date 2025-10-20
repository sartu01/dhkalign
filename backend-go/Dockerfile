# --- build stage ---
FROM golang:1.22-alpine AS build
WORKDIR /src

# Cache deps first (allows remote builder to reuse this when go.mod/go.sum unchanged)
COPY go.mod go.sum* ./
ARG DEPS_SHA=""
RUN echo "$DEPS_SHA" >/dev/null && go mod download

# Copy source and ensure go.sum is fully populated for imports
COPY . .
RUN go mod tidy

# Optional build metadata (passed by CI/Fly)
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
