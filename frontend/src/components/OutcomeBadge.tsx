import type { Outcome } from '../api/client'
import { OUTCOME_LABEL, OUTCOME_TONE } from '../lib/format'
import { Badge } from './ui'

export function OutcomeBadge({ outcome }: { outcome: Outcome }) {
  return <Badge tone={OUTCOME_TONE[outcome]}>{OUTCOME_LABEL[outcome]}</Badge>
}
