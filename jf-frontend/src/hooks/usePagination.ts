import { useState, useCallback } from 'react'

export function usePagination(initialPage = 1) {
  const [page, setPage] = useState(initialPage)

  const goToPage = useCallback((p: number) => setPage(p), [])
  const reset = useCallback(() => setPage(1), [])

  return { page, setPage: goToPage, reset }
}
