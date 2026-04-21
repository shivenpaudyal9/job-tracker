import type { Metadata } from 'next'
import JobsPageClient from './JobsClient'

export const metadata: Metadata = {
  title: 'ML/DS Job Board — Job Market Intelligence by Shiven Paudyal',
  description:
    'Live tracking of ML, Data Science, and MLOps roles from 75+ top companies. Filter by skills, salary, and visa sponsorship.',
  openGraph: {
    title: 'ML/DS Job Board — Job Market Intelligence',
    description: 'Browse 1,200+ ML/DS jobs from top companies. Filter by skill, salary, and visa sponsorship.',
    type: 'website',
  },
}

export default function JobsPage() {
  return <JobsPageClient />
}
