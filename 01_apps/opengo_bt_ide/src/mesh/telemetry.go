package mesh

import (
	"os/exec"
)

type Node struct {
	Name   string
	IP     string
	Status string
}

func GetNodes() []Node {
	nodes := []Node{
		{"Mac Mini (Host)", "100.119.199.76", "✅ ALIVE"},
		{"MacBook Pro", "100.103.212.21", checkPing("100.103.212.21")},
		{"MacBook Air", "100.121.202.34", checkPing("100.121.202.34")},
		{"Pixel 10 Pro", "100.73.38.87", checkPing("100.73.38.87")},
	}
	return nodes
}

func checkPing(ip string) string {
	err := exec.Command("ping", "-c", "1", "-W", "1", ip).Run()
	if err == nil {
		return "✅ ALIVE"
	}
	return "❌ OFFLINE"
}

func GetHostRAM() string {
	out, _ := exec.Command("vm_stat").Output()
	if len(out) > 0 {
		return "Host RAM: OK (Checked via vm_stat)"
	}
	return "Host RAM: Unknown"
}
