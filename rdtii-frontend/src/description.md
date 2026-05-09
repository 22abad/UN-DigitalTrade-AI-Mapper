- Refactor

```
  src/
  ├── main.tsx                          ← entry point only (5 lines)  ├── App.tsx                           ← root component + scroll effect
  ├── styles.css  ├── vite-env.d.ts                                                                                       
  ├── types/
  │   └── index.ts                      ← all shared types
  ├── lib/
  │   ├── constants.ts                  ← API URLs, QUOTE_TRUNCATE, sampleText
  │   └── utils.ts                      ← mappingKey, scoreClass, formatScore, formatFeatureValue
  ├── hooks/
  │   └── useExtraction.ts              ← all state + extract/review logic
  └── components/
      ├── TopBar.tsx
      ├── SourcePanel/
      │   ├── index.tsx
      │   └── SourceView.tsx
      └── AuditPanel/
          ├── index.tsx
          ├── AuditBody.tsx
          ├── MappingCard.tsx
          └── RejectedPanel.tsx
```
