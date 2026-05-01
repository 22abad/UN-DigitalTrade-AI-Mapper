package org.unescap.rdtii.indicater;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/indicators")
public class IndicatorController {

    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> listIndicators(
            @RequestParam(required = false) String pillarId,
            @RequestParam(required = false) String countryCode) {
        return ResponseEntity.ok(List.of());
    }

    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> getIndicator(@PathVariable String id) {
        return ResponseEntity.ok(Map.of("id", id, "message", "Indicator retrieved"));
    }
}
