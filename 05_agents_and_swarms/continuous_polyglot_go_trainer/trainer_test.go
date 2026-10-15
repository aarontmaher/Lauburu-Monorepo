package main

import (
	"os"
	"strings"
	"testing"
)

func TestCurriculumIntegrity(t *testing.T) {
	curriculum := GetPolyglotCurriculum()
	if len(curriculum) < 30 {
		t.Fatalf("Expected at least 30 curriculum items, got %d", len(curriculum))
	}

	tuiCount := 0
	cliCount := 0
	polyCount := 0

	for _, item := range curriculum {
		if item.ID == "" {
			t.Errorf("Curriculum item has empty ID")
		}
		if item.Domain == "" {
			t.Errorf("Curriculum item %s has empty Domain", item.ID)
		}
		if item.Prompt == "" || item.ChosenCode == "" || item.RejectedCode == "" {
			t.Errorf("Curriculum item %s is missing prompt or chosen/rejected code", item.ID)
		}

		sha := item.ComputeSha256()
		if len(sha) != 64 {
			t.Errorf("Curriculum item %s has invalid SHA256 length: %d", item.ID, len(sha))
		}

		if strings.HasPrefix(item.ID, "TUI_") {
			tuiCount++
		} else if strings.HasPrefix(item.ID, "CLI_") {
			cliCount++
		} else {
			polyCount++
		}
	}

	if tuiCount < 10 {
		t.Errorf("Expected at least 10 TUI specialist tasks across all languages, got %d", tuiCount)
	}
	if cliCount < 10 {
		t.Errorf("Expected at least 10 CLI specialist tasks across all languages, got %d", cliCount)
	}
	if polyCount < 11 {
		t.Errorf("Expected at least 11 polyglot systems tasks, got %d", polyCount)
	}
}

func TestCompilerVerificationMultiLang(t *testing.T) {
	trainer := NewPolyglotTrainer(32)

	testCases := []struct {
		name     string
		item     CurriculumItem
		expected bool
	}{
		{
			name: "Valid Go",
			item: CurriculumItem{
				Language:   "go",
				ChosenCode: "package main\n\nfunc main() {}\n",
			},
			expected: true,
		},
		{
			name: "Valid Python",
			item: CurriculumItem{
				Language:   "python",
				ChosenCode: "import sys\nsys.exit(0)\n",
			},
			expected: true,
		},
		{
			name: "Valid C11",
			item: CurriculumItem{
				Language:   "c",
				ChosenCode: "int main(void) { return 0; }\n",
			},
			expected: true,
		},
		{
			name: "Valid C++20",
			item: CurriculumItem{
				Language:   "cpp",
				ChosenCode: "int main() { return 0; }\n",
			},
			expected: true,
		},
		{
			name: "Valid Bash",
			item: CurriculumItem{
				Language:   "bash",
				ChosenCode: "#!/bin/bash\necho ok\n",
			},
			expected: true,
		},
		{
			name: "Valid Swift",
			item: CurriculumItem{
				Language:   "swift",
				ChosenCode: "print(\"ok\")\n",
			},
			expected: true,
		},
		{
			name: "Valid Dart",
			item: CurriculumItem{
				Language:   "dart",
				ChosenCode: "void main() { print(\"ok\"); }\n",
			},
			expected: true,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			passed, exitCode, latency, msg := trainer.ValidateCodeWithCompiler(tc.item)
			if passed != tc.expected {
				t.Errorf("[%s] Expected passed=%v, got %v (exitCode=%d, msg=%s)", tc.name, tc.expected, passed, exitCode, msg)
			}
			if latency < 0 {
				t.Errorf("[%s] Invalid latency: %.2fms", tc.name, latency)
			}
		})
	}
}

func TestExecuteCycleAndPersistence(t *testing.T) {
	trainer := NewPolyglotTrainer(64)
	events := trainer.ExecuteCycle(1001)

	if len(events) != len(trainer.curriculum) {
		t.Errorf("Expected %d events, got %d", len(trainer.curriculum), len(events))
	}

	for _, ev := range events {
		if ev.TaskID == "" {
			t.Errorf("Event has empty TaskID")
		}
		if ev.Sha256Checksum == "" {
			t.Errorf("Event %s has empty SHA256", ev.TaskID)
		}
		if !ev.CompilerVerified {
			t.Errorf("Event %s failed compiler verification: code %d", ev.TaskID, ev.CompilerExitCode)
		}
	}

	// Verify Obsidian ledger was updated
	if _, err := os.Stat(ObsidianLedgerPath); err != nil {
		t.Errorf("Expected Obsidian ledger at %s to exist: %v", ObsidianLedgerPath, err)
	}

	// Verify Data Lake jsonl was updated
	if _, err := os.Stat(DataLakeJsonlPath); err != nil {
		t.Errorf("Expected Data Lake jsonl at %s to exist: %v", DataLakeJsonlPath, err)
	}
}
