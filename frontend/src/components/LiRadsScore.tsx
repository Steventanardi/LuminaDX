import clsx from 'clsx'
import { useI18n } from '../i18n'
import type { TKey } from '../i18n'
import type { LiRadsCategory } from '../types'

const _LIRADS_COLOR: Record<LiRadsCategory, string> = {
  'LR-1':          'bg-green-700  text-green-100',
  'LR-2':          'bg-lime-700   text-lime-100',
  'LR-3':          'bg-yellow-600 text-yellow-100',
  'LR-4':          'bg-orange-600 text-orange-100',
  'LR-5':          'bg-red-700    text-red-100',
  'LR-M':          'bg-purple-700 text-purple-100',
  'LR-TIV':        'bg-pink-700   text-pink-100',
  'Indeterminate': 'bg-gray-600   text-gray-100',
}

const _LIRADS_LABEL_KEY: Record<LiRadsCategory, TKey> = {
  'LR-1':          'lirads.LR-1',
  'LR-2':          'lirads.LR-2',
  'LR-3':          'lirads.LR-3',
  'LR-4':          'lirads.LR-4',
  'LR-5':          'lirads.LR-5',
  'LR-M':          'lirads.LR-M',
  'LR-TIV':        'lirads.LR-TIV',
  'Indeterminate': 'lirads.Indeterminate',
}

function _genericColor(score: string): string {
  const s = score.toLowerCase()
  if (s.includes('high') || s.includes('5') || s.includes('malign') || s.includes('suspicious'))
    return 'bg-red-700 text-red-100'
  if (s.includes('moderate') || s.includes('intermediate') || s.includes('4'))
    return 'bg-orange-600 text-orange-100'
  if (s.includes('low') || s.includes('benign') || s.includes('1') || s.includes('2'))
    return 'bg-green-700 text-green-100'
  return 'bg-gray-600 text-gray-100'
}

interface Props {
  category: LiRadsCategory
  score?: string | null          // generic score string for non-liver cancers
  scoreSystem?: string | null    // e.g. "ABCDE", "BI-RADS", "Lung-RADS"
  size?: 'sm' | 'lg'
}

export default function LiRadsScore({ category, score, scoreSystem, size = 'sm' }: Props) {
  const { t } = useI18n()

  // If we have a generic score (non-LI-RADS), use it
  if (scoreSystem && scoreSystem !== 'LI-RADS' && score) {
    return (
      <span className={clsx(
        'inline-flex flex-wrap items-center gap-1.5 rounded font-bold tracking-wide text-left break-words',
        _genericColor(score),
        size === 'lg' ? 'px-4 py-2 text-sm' : 'px-2 py-1 text-xs',
      )}>
        {scoreSystem && size === 'lg' && (
          <span className="font-normal opacity-70 text-xs shrink-0">{scoreSystem}:</span>
        )}
        <span className={clsx(size === 'lg' ? 'text-base' : '', 'min-w-0 break-words')}>{score}</span>
      </span>
    )
  }

  // LI-RADS badge (default / liver)
  return (
    <span className={clsx(
      'inline-flex flex-wrap items-center gap-2 rounded font-bold tracking-wide text-left break-words',
      _LIRADS_COLOR[category],
      size === 'lg' ? 'px-4 py-2 text-base' : 'px-2 py-1 text-xs',
    )}>
      <span className="shrink-0">{category}</span>
      {size === 'lg' && <span className="font-normal opacity-80 min-w-0 break-words">— {t(_LIRADS_LABEL_KEY[category])}</span>}
    </span>
  )
}
