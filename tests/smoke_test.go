package tests

import (
	"os/exec"
	"path/filepath"
	"testing"
)

func TestBuild(t *testing.T) {
	// Find the absolute path to the repo root (one level above /tests)
	repoRoot, err := filepath.Abs("..")
	if err != nil {
		t.Fatalf("could not determine repo root: %v", err)
	}

	cmd := exec.Command("go", "build", "./cmd/relay")
	cmd.Dir = repoRoot // run from repo root
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("build failed: %v\nOutput:\n%s", err, string(out))
	}
}
