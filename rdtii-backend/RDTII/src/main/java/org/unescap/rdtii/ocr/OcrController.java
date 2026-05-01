package org.unescap.rdtii.ocr;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/ocr")
public class OcrController {

    @PostMapping("/extract")
    public ResponseEntity<Map<String, Object>> extractText(@RequestParam("file") MultipartFile file) {
        return ResponseEntity.ok(Map.of("filename", file.getOriginalFilename(), "message", "OCR extraction started"));
    }

    @GetMapping("/status/{taskId}")
    public ResponseEntity<Map<String, Object>> getOcrStatus(@PathVariable String taskId) {
        return ResponseEntity.ok(Map.of("taskId", taskId, "status", "pending", "message", "OCR task status"));
    }
}
