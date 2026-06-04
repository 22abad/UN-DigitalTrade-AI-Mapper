export interface LegalSource {
  name: string;
  url: string;
  description: string;
}

const LEGAL_SOURCES: Record<string, LegalSource[]> = {
  CN: [
    { name: "National People's Congress", url: "http://www.npc.gov.cn/englishnpc/c2834/index.shtml", description: "Primary legislative body & national laws" },
    { name: "Law Info China", url: "https://www.lawinfochina.com", description: "Bilingual legislation database" },
    { name: "Ministry of Commerce", url: "http://english.mofcom.gov.cn", description: "Trade & e-commerce regulations" },
    { name: "Cyberspace Administration of China", url: "https://www.cac.gov.cn", description: "Data & internet governance laws" },
    { name: "Ministry of Justice", url: "http://english.moj.gov.cn", description: "Official judicial legislation" },
  ],
  IN: [
    { name: "India Code", url: "https://www.indiacode.nic.in", description: "Official central legislation repository" },
    { name: "Legislative Department", url: "https://legislative.gov.in", description: "Ministry of Law & Justice bills" },
    { name: "MeitY", url: "https://www.meity.gov.in", description: "Digital economy & IT regulations" },
    { name: "DPIIT", url: "https://dpiit.gov.in", description: "Trade, IP & investment policy" },
    { name: "TRAI", url: "https://www.trai.gov.in", description: "Telecom & digital services regulation" },
  ],
  SG: [
    { name: "Singapore Statutes Online", url: "https://sso.agc.gov.sg", description: "Official Acts & subsidiary legislation" },
    { name: "PDPC", url: "https://www.pdpc.gov.sg", description: "Personal Data Protection Commission" },
    { name: "IMDA", url: "https://www.imda.gov.sg", description: "Info-communications & media regulation" },
    { name: "MTI", url: "https://www.mti.gov.sg", description: "Ministry of Trade & Industry policy" },
    { name: "MAS", url: "https://www.mas.gov.sg", description: "Monetary Authority & fintech rules" },
  ],
  TH: [
    { name: "Thailand Law Database", url: "https://law.go.th", description: "Official Thai legislation portal" },
    { name: "ETDA", url: "https://www.etda.or.th/en", description: "Electronic Transactions Development Agency" },
    { name: "MDES", url: "https://www.mdes.go.th", description: "Ministry of Digital Economy & Society" },
    { name: "PDPC Thailand", url: "https://www.pdpc.or.th", description: "Personal Data Protection Committee" },
    { name: "BOT", url: "https://www.bot.or.th/en", description: "Bank of Thailand — fintech regulation" },
  ],
  AU: [
    { name: "Federal Register of Legislation", url: "https://www.legislation.gov.au", description: "Official Commonwealth legislation" },
    { name: "OAIC", url: "https://www.oaic.gov.au", description: "Office of Australian Information Commissioner" },
    { name: "ACCC", url: "https://www.accc.gov.au", description: "Competition & digital markets" },
    { name: "DFAT", url: "https://www.dfat.gov.au", description: "Trade agreements & digital trade" },
    { name: "Department of Industry", url: "https://www.industry.gov.au", description: "Digital economy & industry policy" },
  ],
  PH: [
    { name: "Official Gazette", url: "https://www.officialgazette.gov.ph", description: "Philippine laws & executive orders" },
    { name: "LawPhil", url: "https://lawphil.net", description: "Philippine jurisprudence & statutes" },
    { name: "DICT", url: "https://dict.gov.ph", description: "Dept of Information & Communications Technology" },
    { name: "DTI", url: "https://www.dti.gov.ph", description: "Trade & e-commerce regulation" },
    { name: "NPC Philippines", url: "https://www.privacy.gov.ph", description: "National Privacy Commission" },
  ],
  JP: [
    { name: "e-Gov Law Database", url: "https://laws.e-gov.go.jp", description: "Official Japanese statutes (English available)" },
    { name: "Japanese Law Translation", url: "https://www.japaneselawtranslation.go.jp", description: "English translations of key laws" },
    { name: "METI", url: "https://www.meti.go.jp/english", description: "Ministry of Economy, Trade & Industry" },
    { name: "PPC Japan", url: "https://www.ppc.go.jp/en", description: "Personal Information Protection Commission" },
    { name: "MIC Japan", url: "https://www.soumu.go.jp/english", description: "Telecom & digital regulation" },
  ],
  KR: [
    { name: "National Law Information Center", url: "https://www.law.go.kr", description: "Official Korean legislation portal" },
    { name: "MSIT", url: "https://www.msit.go.kr/eng", description: "Ministry of Science & ICT" },
    { name: "PIPC Korea", url: "https://www.pipc.go.kr/eng", description: "Personal Information Protection Commission" },
    { name: "KISA", url: "https://www.kisa.or.kr/eng", description: "Korea Internet & Security Agency" },
    { name: "MOTIE", url: "https://www.motie.go.kr/en", description: "Ministry of Trade, Industry & Energy" },
  ],
  ID: [
    { name: "National Legislation Portal", url: "https://peraturan.go.id", description: "Official Indonesian regulations" },
    { name: "Kominfo", url: "https://www.kominfo.go.id", description: "Ministry of Communications & IT" },
    { name: "OJK", url: "https://www.ojk.go.id/en", description: "Financial Services Authority" },
    { name: "BSSN", url: "https://www.bssn.go.id", description: "National Cyber & Encryption Agency" },
    { name: "Ministry of Trade", url: "https://kemendag.go.id/en", description: "Trade & e-commerce regulation" },
  ],
  MY: [
    { name: "Attorney General's Chambers", url: "https://www.agc.gov.my", description: "Official Malaysian legislation" },
    { name: "MCMC", url: "https://www.mcmc.gov.my", description: "Communications & Multimedia Commission" },
    { name: "PDPD Malaysia", url: "https://www.pdp.gov.my", description: "Personal Data Protection Department" },
    { name: "MITI", url: "https://www.miti.gov.my", description: "Ministry of Investment, Trade & Industry" },
    { name: "SC Malaysia", url: "https://www.sc.com.my", description: "Securities Commission — fintech" },
  ],
  VN: [
    { name: "Vietnam Legal Document Portal", url: "https://vbpl.vn/Pages/portal.aspx", description: "Official Vietnamese legislation" },
    { name: "Ministry of Justice Vietnam", url: "https://moj.gov.vn", description: "Legal & judicial framework" },
    { name: "MIC Vietnam", url: "https://english.mic.gov.vn", description: "Ministry of Information & Communications" },
    { name: "MOIT Vietnam", url: "https://www.moit.gov.vn", description: "Ministry of Industry & Trade" },
    { name: "VCCI", url: "https://vcci.com.vn/en", description: "Vietnam Chamber of Commerce & Industry" },
  ],
  BD: [
    { name: "Bangladesh Laws", url: "http://bdlaws.minlaw.gov.bd", description: "Official Bangladesh legislation" },
    { name: "BTRC", url: "https://www.btrc.gov.bd", description: "Bangladesh Telecom Regulatory Commission" },
    { name: "Ministry of Commerce BD", url: "https://mincom.gov.bd", description: "Trade & commerce regulations" },
    { name: "Bangladesh Bank", url: "https://www.bb.org.bd", description: "Digital payments & fintech rules" },
    { name: "ICT Division", url: "https://ictd.gov.bd", description: "Digital economy policy" },
  ],
  PK: [
    { name: "Pakistan Code", url: "https://pakistancode.gov.pk", description: "Official Pakistan legislation" },
    { name: "PTA", url: "https://www.pta.gov.pk", description: "Pakistan Telecom Authority" },
    { name: "SECP", url: "https://www.secp.gov.pk", description: "Securities & Exchange Commission" },
    { name: "Ministry of Commerce PK", url: "https://commerce.gov.pk", description: "Trade policy & regulation" },
    { name: "NITB", url: "https://www.nitb.gov.pk", description: "National IT Board — digital policy" },
  ],
  LK: [
    { name: "Government Documents Sri Lanka", url: "https://documents.gov.lk", description: "Official Acts & regulations" },
    { name: "TRCSL", url: "https://www.trc.gov.lk", description: "Telecom Regulatory Commission" },
    { name: "SLCERT", url: "https://www.slcert.gov.lk", description: "Cybersecurity regulation" },
    { name: "Central Bank of Sri Lanka", url: "https://www.cbsl.gov.lk", description: "Fintech & payment regulation" },
    { name: "ICTA Sri Lanka", url: "https://www.icta.lk", description: "ICT Agency — digital governance" },
  ],
  NP: [
    { name: "Nepal Law Commission", url: "https://www.lawcommission.gov.np", description: "Official Nepalese legislation" },
    { name: "NTA Nepal", url: "https://nta.gov.np", description: "Nepal Telecommunications Authority" },
    { name: "Ministry of Industry Nepal", url: "https://moics.gov.np", description: "Industry & commerce regulation" },
    { name: "NRB", url: "https://www.nrb.org.np", description: "Nepal Rastra Bank — fintech" },
    { name: "DOCA Nepal", url: "https://www.doc.gov.np", description: "Dept of Commerce — trade policy" },
  ],
  KZ: [
    { name: "Adilet Legal Info", url: "https://adilet.zan.kz/eng", description: "Official Kazakhstan legislation (English)" },
    { name: "Kazakhstan e-Gov", url: "https://www.egov.kz/cms/en", description: "Government digital services portal" },
    { name: "MCIS Kazakhstan", url: "https://www.gov.kz/memleket/entities/mdai/en", description: "Digital development ministry" },
    { name: "NBK", url: "https://nationalbank.kz/?lang=en", description: "National Bank — fintech regulation" },
    { name: "MFCA", url: "https://mfca.kz/en", description: "Astana Financial Centre — digital" },
  ],
  UZ: [
    { name: "Lex.uz", url: "https://lex.uz/en", description: "Official Uzbekistan legislation portal" },
    { name: "Ministry of Justice UZ", url: "https://www.minjust.uz/en", description: "Legal framework & regulation" },
    { name: "MICT Uzbekistan", url: "https://www.mict.uz/en", description: "Ministry of Digital Technologies" },
    { name: "State Customs UZ", url: "https://customs.uz/en", description: "Customs & trade regulations" },
    { name: "Central Bank UZ", url: "https://cbu.uz/en", description: "Digital payment regulation" },
  ],
  MN: [
    { name: "Legal Info Mongolia", url: "https://legalinfo.mn/mn", description: "Official Mongolian legislation" },
    { name: "Ministry of Justice MN", url: "https://mojha.gov.mn/en", description: "Legal & judicial framework" },
    { name: "CRC Mongolia", url: "https://www.crc.gov.mn/en", description: "Communications Regulatory Commission" },
    { name: "General Customs MN", url: "https://www.customs.gov.mn/en", description: "Customs & cross-border trade" },
    { name: "Bank of Mongolia", url: "https://www.mongolbank.mn/eng", description: "Financial & fintech regulation" },
  ],
  NZ: [
    { name: "New Zealand Legislation", url: "https://www.legislation.govt.nz", description: "Official NZ Acts & regulations" },
    { name: "Privacy Commissioner NZ", url: "https://www.privacy.org.nz", description: "Privacy Act & data protection" },
    { name: "MBIE", url: "https://www.mbie.govt.nz", description: "Business, innovation & digital economy" },
    { name: "MFAT NZ", url: "https://www.mfat.govt.nz", description: "Trade agreements & digital trade" },
    { name: "Commerce Commission NZ", url: "https://comcom.govt.nz", description: "Competition & market regulation" },
  ],
  FJ: [
    { name: "Laws of Fiji", url: "https://www.laws.gov.fj", description: "Official Fiji legislation" },
    { name: "FRCA", url: "https://www.frca.org.fj", description: "Fiji Revenue & Customs Authority" },
    { name: "Reserve Bank of Fiji", url: "https://www.rbf.gov.fj", description: "Financial & digital payment rules" },
    { name: "FCCC", url: "https://www.fccc.org.fj", description: "Commerce Commission — competition" },
    { name: "Ministry of Trade Fiji", url: "https://www.mcttt.gov.fj", description: "Trade & digital economy policy" },
  ],
};

export function getLegalSources(countryCode: string): LegalSource[] {
  return LEGAL_SOURCES[countryCode.toUpperCase()] ?? [];
}
