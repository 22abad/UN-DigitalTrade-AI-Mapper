package org.unescap.rdtii.documents;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/documents")
public class DocumentController {

    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> listDocuments() {
        return ResponseEntity.ok(List.of());
    }

    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> getDocument(@PathVariable String id) {
        return ResponseEntity.ok(Map.of("id", id, "message", "Document retrieved"));
    }

    @PostMapping("/upload")
    public ResponseEntity<Map<String, Object>> uploadDocument(@RequestParam("file") MultipartFile file) {
        return ResponseEntity.ok(Map.of("filename", file.getOriginalFilename(), "message", "Document uploaded"));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Map<String, Object>> deleteDocument(@PathVariable String id) {
        return ResponseEntity.ok(Map.of("id", id, "message", "Document deleted"));
    }
}
