import { Document, Image, Page, StyleSheet, Text, View } from '@react-pdf/renderer'
import type { DiagnosticReport, DifferentialItem, LesionFinding, LiRadsCategory, SignOff } from '../types'
import { parseRadiomics, radiomicTagTone, radiomicMetricHelp, radiomicSectionHelp } from './ReportSections'

const LIRADS_COLOR: Record<LiRadsCategory | string, string> = {
  'LR-1':          '#16a34a',
  'LR-2':          '#65a30d',
  'LR-3':          '#d97706',
  'LR-4':          '#ea580c',
  'LR-5':          '#dc2626',
  'LR-M':          '#be185d',
  'LR-TIV':        '#1d4ed8',
  'Indeterminate': '#6b7280',
}

// Likelihood badge colours for the structured differential.
const LK_COLOR: Record<string, string> = {
  high:     '#dc2626',
  moderate: '#d97706',
  low:      '#16a34a',
}

// Per-cancer report title + scoring system shown in the header/footer.
const CANCER_META: Record<string, { title: string; system: string }> = {
  liver:      { title: 'Liver (HCC) AI Diagnostic Report', system: 'LI-RADS v2024' },
  skin:       { title: 'Skin / Melanoma AI Diagnostic Report', system: 'ABCDE · 7-point · Stolz TDS' },
  lung:       { title: 'Lung AI Diagnostic Report', system: 'Lung-RADS v2022' },
  breast:     { title: 'Breast AI Diagnostic Report', system: 'BI-RADS 5th Ed.' },
  colorectal: { title: 'Colorectal AI Diagnostic Report', system: 'C-RADS · TNM (AJCC 8th)' },
}

const s = StyleSheet.create({
  page:          { paddingTop: 48, paddingBottom: 60, paddingHorizontal: 48, fontFamily: 'Helvetica', fontSize: 10, color: '#111827', backgroundColor: '#ffffff' },
  header:        { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', borderBottomWidth: 2, borderBottomColor: '#1a56db', paddingBottom: 10, marginBottom: 16 },
  title:         { fontSize: 17, fontFamily: 'Helvetica-Bold', color: '#111827' },
  meta:          { fontSize: 9, color: '#6b7280', marginTop: 3 },
  ragPill:       { fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#1d4ed8', backgroundColor: '#eff6ff', paddingHorizontal: 7, paddingVertical: 3, borderRadius: 4 },
  topRow:        { flexDirection: 'row', marginBottom: 14 },
  scanImg:       { width: 138, height: 138, backgroundColor: '#000000', borderRadius: 4 },
  impressionBox: { flex: 1, marginLeft: 12, backgroundColor: '#f9fafb', borderWidth: 0.5, borderColor: '#e5e7eb', borderRadius: 6, padding: 10 },
  impression:    { fontSize: 10, color: '#1f2937', lineHeight: 1.6 },
  sec:           { marginBottom: 14 },
  secTitle:      { fontSize: 8.5, fontFamily: 'Helvetica-Bold', color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.8, borderBottomWidth: 0.5, borderBottomColor: '#e5e7eb', paddingBottom: 3, marginBottom: 7 },
  tbl:           { borderWidth: 0.5, borderColor: '#e5e7eb', borderRadius: 4 },
  tblHead:       { flexDirection: 'row', backgroundColor: '#f3f4f6', paddingVertical: 5, paddingHorizontal: 8, borderBottomWidth: 0.5, borderBottomColor: '#e5e7eb' },
  tblHCell:      { fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#6b7280', textTransform: 'uppercase' },
  tblRow:        { flexDirection: 'row', paddingVertical: 5, paddingHorizontal: 8, borderTopWidth: 0.5, borderTopColor: '#f3f4f6' },
  tblCell:       { fontSize: 9, color: '#1f2937' },
  badge:         { borderRadius: 3, paddingHorizontal: 5, paddingVertical: 2, alignSelf: 'flex-start' },
  badgeText:     { fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#ffffff' },
  reasoning:     { fontSize: 9, color: '#374151', marginTop: 4, lineHeight: 1.4 },
  stageTbl:      { borderWidth: 0.5, borderColor: '#e5e7eb', borderRadius: 4, padding: 8 },
  stageRow:      { flexDirection: 'row', paddingVertical: 3, borderBottomWidth: 0.5, borderBottomColor: '#f3f4f6' },
  stageLabel:    { width: 100, fontSize: 9, color: '#6b7280' },
  stageVal:      { flex: 1, fontSize: 10, fontFamily: 'Helvetica-Bold', color: '#c2410c' },
  listItem:      { flexDirection: 'row', marginBottom: 3 },
  listBullet:    { width: 14, fontSize: 10, color: '#1a56db', fontFamily: 'Helvetica-Bold' },
  listText:      { flex: 1, fontSize: 10, color: '#1f2937', lineHeight: 1.4 },
  // Structured differential (for / against per diagnosis)
  dxCard:        { borderWidth: 0.5, borderColor: '#e5e7eb', borderRadius: 4, padding: 8, marginBottom: 6 },
  dxHead:        { flexDirection: 'row', alignItems: 'center', marginBottom: 2 },
  dxName:        { fontSize: 10, fontFamily: 'Helvetica-Bold', color: '#111827', flex: 1 },
  lkBadge:       { borderRadius: 3, paddingHorizontal: 5, paddingVertical: 2 },
  lkText:        { fontSize: 7.5, fontFamily: 'Helvetica-Bold', color: '#ffffff' },
  evLabelFor:    { fontSize: 7.5, fontFamily: 'Helvetica-Bold', color: '#16a34a', textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 3, marginBottom: 1 },
  evLabelAg:     { fontSize: 7.5, fontFamily: 'Helvetica-Bold', color: '#dc2626', textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 3, marginBottom: 1 },
  evRow:         { flexDirection: 'row', marginBottom: 1.5 },
  evMark:        { width: 10, fontSize: 9, fontFamily: 'Helvetica-Bold' },
  evText:        { flex: 1, fontSize: 9, color: '#374151', lineHeight: 1.35 },
  cite:          { fontSize: 9, color: '#6b7280', marginBottom: 2, fontFamily: 'Helvetica-Oblique' },
  signBox:       { borderWidth: 1, borderRadius: 6, padding: 10, marginBottom: 14 },
  signApproved:  { borderColor: '#16a34a', backgroundColor: '#f0fdf4' },
  signChanges:   { borderColor: '#d97706', backgroundColor: '#fffbeb' },
  signTitle:     { fontSize: 9, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' },
  signTitleA:    { color: '#16a34a' },
  signTitleC:    { color: '#d97706' },
  signMeta:      { fontSize: 9, color: '#6b7280', marginTop: 3 },
  signComment:   { fontSize: 9, color: '#6b7280', marginTop: 4, fontFamily: 'Helvetica-Oblique' },
  // Skin lesion detail (ABCDE + dermoscopy features)
  abcdeRow:      { flexDirection: 'row', flexWrap: 'wrap', marginTop: 4, marginBottom: 2 },
  abcdeChip:     { flexDirection: 'row', alignItems: 'center', borderWidth: 0.5, borderColor: '#e5e7eb', borderRadius: 3, paddingHorizontal: 5, paddingVertical: 2, marginRight: 5, marginBottom: 4 },
  abcdeKey:      { fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#6b7280', marginRight: 3 },
  abcdeVal:      { fontSize: 8, fontFamily: 'Helvetica-Bold' },
  featLabel:     { fontSize: 7.5, fontFamily: 'Helvetica-Bold', color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.4, marginTop: 4, marginBottom: 1 },
  featItem:      { fontSize: 9, color: '#374151', marginBottom: 1, lineHeight: 1.35 },
  // Radiomics / quantitative analysis
  radTitle:      { fontSize: 8, fontFamily: 'Helvetica-Bold', color: '#374151', marginTop: 8, marginBottom: 1 },
  radSecHelp:    { fontSize: 8, color: '#9ca3af', marginBottom: 3, lineHeight: 1.4 },
  radRow:        { paddingVertical: 3, borderBottomWidth: 0.5, borderBottomColor: '#f3f4f6' },
  radLine:       { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  radLabel:      { fontSize: 9, color: '#6b7280', flexShrink: 1, paddingRight: 8 },
  radValWrap:    { flexDirection: 'row', alignItems: 'center', flexShrink: 0 },
  radValue:      { fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#1f2937' },
  radValueLong:  { fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#1f2937', marginTop: 2, lineHeight: 1.4 },
  radTag:        { fontSize: 7, fontFamily: 'Helvetica-Bold', borderRadius: 3, paddingHorizontal: 4, paddingVertical: 1, marginLeft: 5 },
  radHint:       { fontSize: 8, color: '#9ca3af', marginTop: 1.5, lineHeight: 1.35 },
  radHelp:       { fontSize: 8, color: '#9ca3af', fontFamily: 'Helvetica-Oblique', marginTop: 1.5, lineHeight: 1.35 },
  radResult:     { fontSize: 9, fontFamily: 'Helvetica-Bold', color: '#1f2937', backgroundColor: '#f9fafb', borderRadius: 3, paddingHorizontal: 6, paddingVertical: 4, marginTop: 4 },
  radWarn:       { fontSize: 8.5, color: '#92400e', marginTop: 3, lineHeight: 1.4 },
  radNote:       { fontSize: 8, color: '#9ca3af', fontFamily: 'Helvetica-Oblique', marginTop: 3, lineHeight: 1.4 },
  rawBox:        { borderWidth: 0.5, borderColor: '#e5e7eb', backgroundColor: '#f9fafb', borderRadius: 4, padding: 8 },
  rawTxt:        { fontSize: 8, fontFamily: 'Courier', color: '#374151', lineHeight: 1.45 },
  disclaimer:    { borderWidth: 1, borderColor: '#f59e0b', backgroundColor: '#fffbeb', borderRadius: 4, padding: 8, marginTop: 8 },
  disclaimerTxt: { fontSize: 8.5, color: '#92400e', lineHeight: 1.5 },
  footer:        { position: 'absolute', bottom: 24, left: 48, right: 48, flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 0.5, borderTopColor: '#e5e7eb', paddingTop: 6 },
  footerTxt:     { fontSize: 8, color: '#9ca3af' },
})

function bool(v: boolean | null | undefined) {
  return v === null || v === undefined ? '—' : v ? 'Yes' : 'No'
}

// Slices come through as raw base64 of the on-disk image — JPEG for CT/MRI, but
// PNG for the enhanced skin/dermoscopy frame. react-pdf decodes strictly by the
// declared mime (unlike a browser <img>, which sniffs), so a PNG mislabelled
// image/jpeg renders as a black box. Sniff the magic bytes and label correctly.
function sliceDataUri(b64: string): string {
  const mime = b64.startsWith('iVBOR') ? 'image/png'
    : b64.startsWith('R0lGOD') ? 'image/gif'
    : b64.startsWith('UklGR') ? 'image/webp'
    : 'image/jpeg'
  return `data:${mime};base64,${b64}`
}

// @react-pdf's standard fonts (Helvetica/Courier) only cover WinAnsi/Latin-1, so
// glyphs the LLM/radiomics emit — arrows, ≥/≤, check marks — render as garbage or
// vanish. Map the common ones to ASCII and drop anything else outside Latin-1
// (keeping the cp1252 typographic extras: – — ' ' " " … •).
function pdfSafe(v: string | null | undefined): string {
  if (!v) return ''
  return v
    .replace(/[→⟶➔➙➜]/g, '->')
    .replace(/←/g, '<-')
    .replace(/≥/g, '>=').replace(/≤/g, '<=').replace(/≠/g, '!=')
    .replace(/[✓✔]/g, 'Yes').replace(/[✗✘✕]/g, 'No')
    .replace(/≈/g, '~').replace(/×/g, 'x')
    .replace(/[^\x09\x0a\x0d\x20-\xff–—‘’“”…•]/g, '')
}

interface Props {
  report: DiagnosticReport
  signOff: SignOff | null
  currentSlice?: string
}

function DifferentialCard({ d, i }: { d: DifferentialItem; i: number }) {
  const lk = (d.likelihood ?? '').toLowerCase()
  return (
    <View style={s.dxCard} wrap={false}>
      <View style={s.dxHead}>
        <Text style={s.dxName}>{i + 1}. {pdfSafe(d.diagnosis)}</Text>
        {d.likelihood && (
          <View style={{ ...s.lkBadge, backgroundColor: LK_COLOR[lk] ?? '#6b7280' }}>
            <Text style={s.lkText}>{d.likelihood.toUpperCase()}</Text>
          </View>
        )}
      </View>
      {d.supporting_features.length > 0 && (
        <View>
          <Text style={s.evLabelFor}>Supports</Text>
          {d.supporting_features.map((f, j) => (
            <View key={j} style={s.evRow}>
              <Text style={{ ...s.evMark, color: '#16a34a' }}>+</Text>
              <Text style={s.evText}>{pdfSafe(f)}</Text>
            </View>
          ))}
        </View>
      )}
      {d.opposing_features.length > 0 && (
        <View>
          <Text style={s.evLabelAg}>Against</Text>
          {d.opposing_features.map((f, j) => (
            <View key={j} style={s.evRow}>
              <Text style={{ ...s.evMark, color: '#dc2626' }}>-</Text>
              <Text style={s.evText}>{pdfSafe(f)}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  )
}

// Skin / generic lesion detail: ABCDE flags + major / ancillary dermoscopy features
// (the on-screen panel shows these, but the PDF previously dropped them entirely).
const ABCDE_LABELS: [string, string][] = [
  ['A_asymmetry', 'A'], ['B_border', 'B'], ['C_color', 'C'], ['D_diameter', 'D'], ['E_evolution', 'E'],
]
function LesionDetail({ l }: { l: LesionFinding }) {
  const abcde = l.abcde ?? null
  const hasAbcde = abcde && Object.values(abcde).some(v => v !== null && v !== undefined)
  if (!hasAbcde && l.major_features.length === 0 && l.ancillary_features.length === 0) return null
  return (
    <View style={{ marginTop: 4, marginBottom: 2 }} wrap={false}>
      <Text style={{ ...s.tblCell, fontFamily: 'Helvetica-Bold', marginBottom: 1 }}>{l.lesion_id}</Text>
      {hasAbcde && (
        <View style={s.abcdeRow}>
          {ABCDE_LABELS.map(([key, short]) => {
            const v = abcde![key]
            const color = v === null || v === undefined ? '#9ca3af' : v ? '#dc2626' : '#16a34a'
            return (
              <View key={key} style={s.abcdeChip}>
                <Text style={s.abcdeKey}>{short}</Text>
                <Text style={{ ...s.abcdeVal, color }}>{v === null || v === undefined ? '—' : v ? 'Yes' : 'No'}</Text>
              </View>
            )
          })}
        </View>
      )}
      {l.major_features.length > 0 && (
        <>
          <Text style={s.featLabel}>Major features</Text>
          {l.major_features.map((f, j) => <Text key={j} style={s.featItem}>• {pdfSafe(f)}</Text>)}
        </>
      )}
      {l.ancillary_features.length > 0 && (
        <>
          <Text style={s.featLabel}>Ancillary features</Text>
          {l.ancillary_features.map((f, j) => <Text key={j} style={s.featItem}>- {pdfSafe(f)}</Text>)}
        </>
      )}
    </View>
  )
}

const RAD_TAG_COLOR = {
  alert:   { backgroundColor: '#fef2f2', color: '#dc2626' },
  ok:      { backgroundColor: '#f0fdf4', color: '#16a34a' },
  neutral: { backgroundColor: '#f3f4f6', color: '#6b7280' },
}
const RAD_RESULT_COLOR = {
  alert:   { backgroundColor: '#fef2f2', color: '#b91c1c' },
  ok:      { backgroundColor: '#f0fdf4', color: '#15803d' },
  neutral: { backgroundColor: '#f9fafb', color: '#1f2937' },
}
function RadiomicsPdf({ summary }: { summary: string }) {
  return (
    <View style={s.sec}>
      <Text style={s.secTitle}>Quantitative Image Analysis</Text>
      {parseRadiomics(summary).map((c, i) => {
        if (c.kind === 'title') {
          const help = radiomicSectionHelp(c.text)
          return (
            <View key={i} wrap={false}>
              <Text style={s.radTitle}>{pdfSafe(c.text)}</Text>
              {help && <Text style={s.radSecHelp}>{pdfSafe(help)}</Text>}
            </View>
          )
        }
        if (c.kind === 'metric') {
          const help = radiomicMetricHelp(c.label)
          // Long values (neighbour lists, multi-word measurements) get their own
          // full-width line so they wrap cleanly instead of overflowing the row.
          const stacked = c.value.length > 42
          return (
            <View key={i} style={s.radRow} wrap={false}>
              <View style={s.radLine}>
                <Text style={s.radLabel}>{pdfSafe(c.label)}</Text>
                {stacked
                  ? (c.tag && <Text style={{ ...s.radTag, ...RAD_TAG_COLOR[radiomicTagTone(c.tag)] }}>{pdfSafe(c.tag)}</Text>)
                  : (
                    <View style={s.radValWrap}>
                      <Text style={s.radValue}>{pdfSafe(c.value)}</Text>
                      {c.tag && <Text style={{ ...s.radTag, ...RAD_TAG_COLOR[radiomicTagTone(c.tag)] }}>{pdfSafe(c.tag)}</Text>}
                    </View>
                  )}
              </View>
              {stacked && <Text style={s.radValueLong}>{pdfSafe(c.value)}</Text>}
              {c.hint && <Text style={s.radHint}>{pdfSafe(c.hint)}</Text>}
              {help && <Text style={s.radHelp}>{pdfSafe(help)}</Text>}
            </View>
          )
        }
        if (c.kind === 'result')  return (
          <Text key={i} style={{ ...s.radResult, ...RAD_RESULT_COLOR[radiomicTagTone(c.text)] }}>{pdfSafe(c.text)}</Text>
        )
        if (c.kind === 'warning') return <Text key={i} style={s.radWarn}>! {pdfSafe(c.text)}</Text>
        if (c.kind === 'note')    return <Text key={i} style={s.radNote}>{pdfSafe(c.text)}</Text>
        return <Text key={i} style={{ ...s.radNote, fontFamily: 'Helvetica' }}>{pdfSafe(c.text)}</Text>
      })}
    </View>
  )
}

export default function ReportPDF({ report, signOff, currentSlice }: Props) {
  const dateStr = new Date(report.generated_at).toLocaleString()
  const meta = CANCER_META[report.cancer_type] ?? { title: 'LuminaDx AI Diagnostic Report', system: '' }
  const isLiver = report.cancer_type === 'liver'
  const diffAssessment = report.differential_assessment ?? []
  // When JSON parsing failed the backend returns only a placeholder impression
  // ("Analysis complete — see raw output.") with no structured body — fall back to
  // the raw model text so the PDF is never an empty page.
  const hasStructured =
    report.lesions.length > 0 ||
    report.differential_diagnosis.length > 0 ||
    diffAssessment.length > 0 ||
    report.recommendations.length > 0
  const showRaw = !hasStructured && !!report.raw_llm_output

  return (
    <Document title={meta.title} author="LuminaDx">
      <Page size="A4" style={s.page}>

        {/* Header */}
        <View style={s.header}>
          <View>
            <Text style={s.title}>{meta.title}</Text>
            <Text style={s.meta}>Generated: {dateStr}  ·  Modality: {report.modality}</Text>
          </View>
          {report.rag_context_used && <Text style={s.ragPill}>RAG-Augmented</Text>}
        </View>

        {/* DICOM thumbnail + Overall impression */}
        <View style={s.topRow}>
          {currentSlice && (
            <Image style={s.scanImg} src={sliceDataUri(currentSlice)} />
          )}
          <View style={currentSlice ? s.impressionBox : { ...s.impressionBox, marginLeft: 0 }}>
            <Text style={{ ...s.secTitle, borderBottomWidth: 0, marginBottom: 5 }}>Overall Impression</Text>
            <Text style={s.impression}>{pdfSafe(report.overall_impression)}</Text>
          </View>
        </View>

        {/* Raw model output — fallback when structured parsing failed (no lesions/dx) */}
        {showRaw && (
          <View style={s.sec}>
            <Text style={s.secTitle}>Model Output</Text>
            <View style={s.rawBox}>
              <Text style={s.rawTxt}>{pdfSafe(report.raw_llm_output)}</Text>
            </View>
          </View>
        )}

        {/* Lesions table — detailed LI-RADS columns for liver, generic score table otherwise */}
        {report.lesions.length > 0 && (
          <View style={s.sec}>
            <Text style={s.secTitle}>Lesions ({report.lesions.length})</Text>
            <View style={s.tbl}>
              {isLiver ? (
                <>
                  <View style={s.tblHead}>
                    {[['ID', 1], ['LI-RADS', 1.2], ['Size', 0.9], ['Location', 1.8], ['APHE', 0.8], ['Washout', 0.9], ['Capsule', 0.9]].map(
                      ([h, f]) => (
                        <Text key={String(h)} style={{ ...s.tblHCell, flex: Number(f) }}>{String(h)}</Text>
                      )
                    )}
                  </View>
                  {report.lesions.map(l => (
                    <View key={l.lesion_id} style={s.tblRow}>
                      <Text style={{ ...s.tblCell, flex: 1, fontFamily: 'Helvetica-Bold' }}>{l.lesion_id}</Text>
                      <View style={{ flex: 1.2 }}>
                        <View style={{ ...s.badge, backgroundColor: LIRADS_COLOR[l.lirads_category] ?? '#6b7280' }}>
                          <Text style={s.badgeText}>{l.lirads_category}</Text>
                        </View>
                      </View>
                      <Text style={{ ...s.tblCell, flex: 0.9 }}>{l.size_mm != null ? `${l.size_mm} mm` : '—'}</Text>
                      <Text style={{ ...s.tblCell, flex: 1.8 }}>{pdfSafe(l.location_segment) || '—'}</Text>
                      <Text style={{ ...s.tblCell, flex: 0.8 }}>{bool(l.aphe_present)}</Text>
                      <Text style={{ ...s.tblCell, flex: 0.9 }}>{bool(l.washout_present)}</Text>
                      <Text style={{ ...s.tblCell, flex: 0.9 }}>{bool(l.capsule_present)}</Text>
                    </View>
                  ))}
                </>
              ) : (
                <>
                  <View style={s.tblHead}>
                    {[['ID', 0.8], ['Score', 1.5], ['Size', 0.9], ['Location', 2.6]].map(([h, f]) => (
                      <Text key={String(h)} style={{ ...s.tblHCell, flex: Number(f) }}>{String(h)}</Text>
                    ))}
                  </View>
                  {report.lesions.map(l => (
                    <View key={l.lesion_id} style={s.tblRow}>
                      <Text style={{ ...s.tblCell, flex: 0.8, fontFamily: 'Helvetica-Bold' }}>{l.lesion_id}</Text>
                      <View style={{ flex: 1.5 }}>
                        {l.score
                          ? <View style={{ ...s.badge, backgroundColor: '#475569' }}><Text style={s.badgeText}>{l.score}</Text></View>
                          : <Text style={s.tblCell}>—</Text>}
                        {l.score_system && <Text style={{ fontSize: 7, color: '#9ca3af', marginTop: 2 }}>{l.score_system}</Text>}
                      </View>
                      <Text style={{ ...s.tblCell, flex: 0.9 }}>{l.size_mm != null ? `${l.size_mm} mm` : '—'}</Text>
                      <Text style={{ ...s.tblCell, flex: 2.6 }}>{pdfSafe(l.location_segment) || '—'}</Text>
                    </View>
                  ))}
                </>
              )}
            </View>
            {/* Non-liver: ABCDE flags + dermoscopy features per lesion (PDF used to omit these) */}
            {!isLiver && report.lesions.map(l => <LesionDetail key={`det-${l.lesion_id}`} l={l} />)}
            {report.lesions.filter(l => l.reasoning).map(l => (
              <Text key={`rsn-${l.lesion_id}`} style={s.reasoning}>
                <Text style={{ fontFamily: 'Helvetica-Bold' }}>{l.lesion_id}: </Text>{pdfSafe(l.reasoning)}
              </Text>
            ))}
          </View>
        )}

        {/* Staging — BCLC/vascular for liver, generic staging string for other cancers */}
        {(report.bclc_stage || report.vascular_involvement || report.staging) && (
          <View style={s.sec}>
            <Text style={s.secTitle}>Staging</Text>
            <View style={s.stageTbl}>
              {report.bclc_stage && (
                <View style={s.stageRow}>
                  <Text style={s.stageLabel}>BCLC Stage</Text>
                  <Text style={s.stageVal}>{report.bclc_stage}</Text>
                </View>
              )}
              {report.vascular_involvement && (
                <View style={s.stageRow}>
                  <Text style={s.stageLabel}>Vascular</Text>
                  <Text style={{ ...s.stageVal, color: '#111827', fontFamily: 'Helvetica' }}>{pdfSafe(report.vascular_involvement)}</Text>
                </View>
              )}
              {report.staging && (
                <View style={{ ...s.stageRow, borderBottomWidth: 0 }}>
                  <Text style={s.stageLabel}>Stage</Text>
                  <Text style={{ ...s.stageVal, color: '#111827', fontFamily: 'Helvetica' }}>{pdfSafe(report.staging)}</Text>
                </View>
              )}
            </View>
          </View>
        )}

        {/* Differential Diagnosis — structured for/against when available, else flat list */}
        {diffAssessment.length > 0 ? (
          <View style={s.sec}>
            <Text style={s.secTitle}>Differential Diagnosis</Text>
            {diffAssessment.map((d, i) => (
              <DifferentialCard key={`${d.diagnosis}-${i}`} d={d} i={i} />
            ))}
          </View>
        ) : report.differential_diagnosis.length > 0 ? (
          <View style={s.sec}>
            <Text style={s.secTitle}>Differential Diagnosis</Text>
            {report.differential_diagnosis.map((d, i) => (
              <View key={d} style={s.listItem}>
                <Text style={{ ...s.listBullet }}>{i + 1}.</Text>
                <Text style={s.listText}>{pdfSafe(d)}</Text>
              </View>
            ))}
          </View>
        ) : null}

        {/* Recommendations */}
        {report.recommendations.length > 0 && (
          <View style={s.sec}>
            <Text style={s.secTitle}>Recommendations</Text>
            {report.recommendations.map(r => (
              <View key={r} style={s.listItem}>
                <Text style={s.listBullet}>-</Text>
                <Text style={s.listText}>{pdfSafe(r)}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Guideline Citations */}
        {report.guideline_citations.length > 0 && (
          <View style={s.sec}>
            <Text style={s.secTitle}>Guideline Citations</Text>
            {report.guideline_citations.map(c => (
              <Text key={c} style={s.cite}>[{c}]</Text>
            ))}
          </View>
        )}

        {/* Quantitative image analysis (ABCD/TDS + CNN/classifier) — friendly rows */}
        {report.radiomics_summary && !report.radiomics_summary.startsWith('Feature extraction unavailable') && (
          <RadiomicsPdf summary={report.radiomics_summary} />
        )}

        {/* Radiologist Sign-off */}
        {signOff && (
          <View style={[s.signBox, signOff.decision === 'approved' ? s.signApproved : s.signChanges]}>
            <Text style={[s.signTitle, signOff.decision === 'approved' ? s.signTitleA : s.signTitleC]}>
              {signOff.decision === 'approved' ? 'Approved' : 'Changes Requested'}
            </Text>
            <Text style={s.signMeta}>
              Radiologist: {signOff.radiologist_name}  ·  {new Date(signOff.signed_at).toLocaleString()}
            </Text>
            {signOff.comments && (
              <Text style={s.signComment}>"{signOff.comments}"</Text>
            )}
          </View>
        )}

        {/* Disclaimer */}
        <View style={s.disclaimer}>
          <Text style={s.disclaimerTxt}>
            AI-assisted decision support only. All findings must be reviewed and confirmed by a licensed radiologist before any clinical use. This report does not constitute a clinical diagnosis.
          </Text>
        </View>

        {/* Page footer */}
        <View style={s.footer} fixed>
          <Text style={s.footerTxt}>LuminaDx{meta.system ? `  ·  ${meta.system}` : ''}{report.rag_context_used ? '  ·  RAG-Augmented' : ''}</Text>
          <Text style={s.footerTxt} render={({ pageNumber, totalPages }) => `Page ${pageNumber} / ${totalPages}`} />
        </View>

      </Page>
    </Document>
  )
}
