package main

import "C"
import (
	"context"
	"log"
	"os"

	"tailscale.com/tsnet"
)

var server *tsnet.Server

//export StartTsnet
func StartTsnet(headscaleURL *C.char, authKey *C.char, hostname *C.char) int {
	goURL := C.GoString(headscaleURL)
	goAuth := C.GoString(authKey)
	goHost := C.GoString(hostname)

	os.MkdirAll("/tmp/openclaw-tsnet", 0700)

	server = &tsnet.Server{
		Dir:        "/tmp/openclaw-tsnet",
		Hostname:   goHost,
		AuthKey:    goAuth,
		ControlURL: goURL,
		Ephemeral:  false,
	}

	if err := server.Start(); err != nil {
		log.Printf("Failed to start tsnet: %v", err)
		return 1
	}

	lc, err := server.LocalClient()
	if err != nil {
		log.Printf("Failed to get local client: %v", err)
		return 1
	}
	
	status, err := lc.StatusWithoutPeers(context.Background())
	if err == nil && len(status.TailscaleIPs) > 0 {
		log.Printf("Successfully joined mesh with IP: %s", status.TailscaleIPs[0].String())
	}

	return 0
}

//export GetTsnetIP
func GetTsnetIP() *C.char {
	if server == nil {
		return C.CString("")
	}
	lc, err := server.LocalClient()
	if err != nil {
		return C.CString("")
	}
	status, err := lc.StatusWithoutPeers(context.Background())
	if err != nil || len(status.TailscaleIPs) == 0 {
		return C.CString("")
	}
	return C.CString(status.TailscaleIPs[0].String())
}

//export StopTsnet
func StopTsnet() {
	if server != nil {
		server.Close()
	}
}

func main() {}
