export const API_URL =
  import.meta.env.VITE_EXTRACT_API_URL ?? "http://localhost:8000/api/extract";

export const REVIEW_API_URL =
  import.meta.env.VITE_REVIEW_API_URL ?? "http://localhost:8000/api/mappings/review";

export const QUOTE_TRUNCATE = 280;

export const sampleText = `Article 22. Personal information processors may provide personal information outside the territory only where the conditions prescribed by law are satisfied.

Article 23. Where personal information is provided outside the territory, individuals shall be informed of the overseas recipient, processing purpose, method, and rights procedures.`;
