package mesh

import (
	"log"
	"net"

	"tailscale.com/tsnet"
	"github.com/aarontmaher/lauburu-opencode/internal/config"
)

type MeshServer struct {
	srv *tsnet.Server
}

func StartMesh(cfg *config.Config) (*MeshServer, error) {
	s := &tsnet.Server{
		Hostname: "lauburu-opencode-edge",
		AuthKey:  cfg.AuthKey,
	}

	if err := s.Start(); err != nil {
		return nil, err
	}

	log.Println("Joined Lauburu Mesh via userspace Tailscale")
	return &MeshServer{srv: s}, nil
}

func (m *MeshServer) Listen(network, addr string) (net.Listener, error) {
	return m.srv.Listen(network, addr)
}

func (m *MeshServer) Close() {
	m.srv.Close()
}
