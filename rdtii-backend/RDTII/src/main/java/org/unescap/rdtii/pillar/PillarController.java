package org.unescap.rdtii.pillar;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/pillars")
public class PillarController {

    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> listPillars() {
        return ResponseEntity.ok(List.of());
    }

    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> getPillar(@PathVariable String id) {
        return ResponseEntity.ok(Map.of("id", id, "message", "Pillar retrieved"));
    }

    @GetMapping("/{id}/criteria")
    public ResponseEntity<List<Map<String, Object>>> getPillarCriteria(@PathVariable String id) {
        return ResponseEntity.ok(List.of());
    }
}
