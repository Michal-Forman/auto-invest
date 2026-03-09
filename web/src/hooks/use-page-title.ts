import { useEffect } from "react";

export function usePageTitle(page: string) {
  useEffect(() => {
    document.title = `auto invest | ${page}`;
    return () => {
      document.title = "auto invest";
    };
  }, [page]);
}
