// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT

package main

import (
	"fmt"
	"net/http"
	"strings"
)

// Simple text processing function
func processText(text string) string {
	// Trim and normalize spaces
	words := strings.Fields(text)
	return strings.Join(words, " ")
}

// HTTP handler for text processing
func textHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	text := r.FormValue("text")
	if text == "" {
		http.Error(w, "No text provided", http.StatusBadRequest)
		return
	}

	processed := processText(text)
	fmt.Fprintf(w, processed)
}

func main() {
	http.HandleFunc("/process", textHandler)
	fmt.Println("Go service running on :8080")
	http.ListenAndServe(":8080", nil)
}
