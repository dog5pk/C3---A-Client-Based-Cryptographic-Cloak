package log

import (
	"fmt"
	"time"
)

// log prints a single line with a timestamp and level.
// Simple on purpose; we can swap this later for structured JSON.
func log(level, msg string) {
	ts := time.Now().Format(time.RFC3339)
	fmt.Printf("[%s] %s: %s\n", ts, level, msg)
}

func Info(msg string)  { log("INFO", msg) }
func Warn(msg string)  { log("WARN", msg) }
func Error(msg string) { log("ERROR", msg) }
func Debug(msg string) { log("DEBUG", msg) }
