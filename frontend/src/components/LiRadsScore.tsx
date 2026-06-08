import clsx from 'clsx'
import type { LiRadsCategory } from '../types'

const _COLOR: Record<LiRadsCategory, string> = {
  'LR-1':          'bg-green-700  text-green-100',
  'LR-2':          'bg-lime-700   text-lime-100',
  'LR-3':          'bg-yellow-600 text-yellow-100',
  'LR-4':          'bg-orange-600 text-orange-100',
  'LR-5':          'bg-red-700    text-red-100',
  'LR-M':          'bg-purple-700 text-purple-100',
  'LR-TIV':        'bg-pink-700   text-pink-100',
  'Indeterminate': 'bg-gray-600   text-gray-100',
}

const _LABEL: Record<LiRadsCategory, string> = {
  'LR-1':          'Definitely Benign',
  'LR-2':          'Probably Benign',
  'LR-3':          'Intermediate',
  'LR-4':          'Probably HCC',
  'LR-5':          'Definitely HCC',
  'LR-M':          'Malignant (non-HCC)',
  'LR-TIV':        'Tumour in Vein',
  'Indeterminate': 'Indeterminate',
}

interface Props {
  category: LiRadsCategory
  size?: 'sm' | 'lg'
}

export default function LiRadsScore({ category, size = 'sm' }: Props) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-2 rounded font-bold tracking-wide',
        _COLOR[category],
        size === 'lg' ? 'px-4 py-2 text-base' : 'px-2 py-1 text-xs',
      )}
    >
      <span>{category}</span>
      {size === 'lg' && <span className="font-normal opacity-80">— {_LABEL[category]}</span>}
    </span>
  )
}

