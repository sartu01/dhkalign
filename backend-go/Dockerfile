FROM golang:1.22-alpine AS build
WORKDIR /src
COPY backend-go/go.mod backend-go/go.sum* backend-go/
WORKDIR /src/backend-go
RUN go mod download
COPY backend-go /src/backend-go
RUN CGO_ENABLED=0 go build -o /out/server

FROM gcr.io/distroless/base-debian12
ENV PORT=8080
EXPOSE 8080
COPY --from=build /out/server /server
USER nonroot:nonroot
CMD ["/server"]
