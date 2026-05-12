export function useFormat() {
  function formatDate(value: string | null | undefined) {
    if (!value) {
      return 'Unknown'
    }
    return new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value))
  }

  function formatBytes(value: number) {
    if (value < 1024) {
      return `${value} B`
    }
    if (value < 1024 * 1024) {
      return `${(value / 1024).toFixed(1)} KB`
    }
    return `${(value / 1024 / 1024).toFixed(1)} MB`
  }

  return {
    formatDate,
    formatBytes,
  }
}
