# Build the Go brain (radiod) and ship a small runtime image with ffmpeg
# (for audio metadata/transcode) and CA certs (for slskd/LLM/HTTP calls).
FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /radiod ./cmd/radiod

FROM alpine:3.20
RUN apk add --no-cache ca-certificates ffmpeg tzdata yt-dlp python3
COPY --from=build /radiod /usr/local/bin/radiod
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/radiod"]
