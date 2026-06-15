import { Document, Image, Page, StyleSheet, Text, View } from '@react-pdf/renderer'
import type { DiagnosticReport, LiRadsCategory, SignOff } from '../types'

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
  cite:          { fontSize: 9, color: '#6b7280', marginBottom: 2, fontFamily: 'Helvetica-Oblique' },
  signBox:       { borderWidth: 1, borderRadius: 6, padding: 10, marginBottom: 14 },
  signApproved:  { borderColor: '#16a34a', backgroundColor: '#f0fdf4' },
  signChanges:   { borderColor: '#d97706', backgroundColor: '#fffbeb' },
  signTitle:     { fontSize: 9, fontFamily: 'Helvetica-Bold', textTransform: 'uppercase' },
  signTitleA:    { color: '#16a34a' },
  signTitleC:    { color: '#d97706' },
  signMeta:      { fontSize: 9, color: '#6b7280', marginTop: 3 },
  signComment:   { fontSize: 9, color: '#6b7280', marginTop: 4, fontFamily: 'Helvetica-Oblique' },
  disclaimer:    { borderWidth: 1, borderColor: '#f59e0b', backgroundColor: '#fffbeb', borderRadius: 4, padding: 8, marginTop: 8 },
  disclaimerTxt: { fontSize: 8.5, color: '#92400e', lineHeight: 1.5 },
  footer:        { position: 'absolute', bottom: 24, left: 48, right: 48, flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 0.5, borderTopColor: '#e5e7eb', paddingTop: 6 },
  footerTxt:     { fontSize: 8, color: '#9ca3af' },
})

function bool(v: boolean | null | undefined) {
  return v === null || v === undefined ? '—' : v ? 'Yes' : 'No'
}

interface Props {
  report: DiagnosticReport
  signOff: SignOff | null
  currentSlice?: string
}

export default function ReportPDF({ report, signOff, currentSlice }: Props) {
  const dateStr = new Date(report.generated_at).toLocaleString()

  return (
    <Document title="Liver Cancer AI Diagnostic Report" author="Liver Cancer AI">
      <Page size="A4" style={s.page}>

        {/* Header */}
        <View style={s.header}>
          <View>
            <Text style={s.title}>Liver Cancer AI Diagnostic Report</Text>
            <Text style={s.meta}>Generated: {dateStr}  ·  Modality: {report.modality}</Text>
          </View>
          {report.rag_context_used && <Text style={s.ragPill}>RAG-Augmented</Text>}
        </View>

        {/* DICOM thumbnail + Overall impression */}
        <View style={s.topRow}>
          {currentSlice && (
            <Image style={s.scanImg} src={`data:image/jpeg;base64,${currentSlice}`} />
          )}
          <View style={currentSlice ? s.impressionBox : { ...s.impressionBox, marginLeft: 0 }}>
            <Text style={{ ...s.secTitle, borderBottomWidth: 0, marginBottom: 5 }}>Overall Impression</Text>
            <Text style={s.impression}>{report.overall_impression}</Text>
          </View>
        </View>

        {/* Lesions table */}
        {report.lesions.length > 0 && (
          <View style={s.sec}>
            <Text style={s.secTitle}>Lesions ({report.lesions.length})</Text>
            <View style={s.tbl}>
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
                  <Text style={{ ...s.tblCell, flex: 1.8 }}>{l.location_segment ?? '—'}</Text>
                  <Text style={{ ...s.tblCell, flex: 0.8 }}>{bool(l.aphe_present)}</Text>
                  <Text style={{ ...s.tblCell, flex: 0.9 }}>{bool(l.washout_present)}</Text>
                  <Text style={{ ...s.tblCell, flex: 0.9 }}>{bool(l.capsule_present)}</Text>
                </View>
              ))}
            </View>
            {report.lesions.filter(l => l.reasoning).map(l => (
              <Text key={`rsn-${l.lesion_id}`} style={s.reasoning}>
                <Text style={{ fontFamily: 'Helvetica-Bold' }}>{l.lesion_id}: </Text>{l.reasoning}
              </Text>
            ))}
          </View>
        )}

        {/* Staging */}
        {(report.bclc_stage || report.vascular_involvement) && (
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
                <View style={{ ...s.stageRow, borderBottomWidth: 0 }}>
                  <Text style={s.stageLabel}>Vascular</Text>
                  <Text style={{ ...s.stageVal, color: '#111827', fontFamily: 'Helvetica' }}>{report.vascular_involvement}</Text>
                </View>
              )}
            </View>
          </View>
        )}

        {/* Differential Diagnosis */}
        {report.differential_diagnosis.length > 0 && (
          <View style={s.sec}>
            <Text style={s.secTitle}>Differential Diagnosis</Text>
            {report.differential_diagnosis.map((d, i) => (
              <View key={d} style={s.listItem}>
                <Text style={{ ...s.listBullet }}>{i + 1}.</Text>
                <Text style={s.listText}>{d}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Recommendations */}
        {report.recommendations.length > 0 && (
          <View style={s.sec}>
            <Text style={s.secTitle}>Recommendations</Text>
            {report.recommendations.map(r => (
              <View key={r} style={s.listItem}>
                <Text style={s.listBullet}>-</Text>
                <Text style={s.listText}>{r}</Text>
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
          <Text style={s.footerTxt}>Liver Cancer AI  ·  LI-RADS v2024  ·  RAG-Augmented</Text>
          <Text style={s.footerTxt} render={({ pageNumber, totalPages }) => `Page ${pageNumber} / ${totalPages}`} />
        </View>

      </Page>
    </Document>
  )
}
