import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AnalysisProvider } from './contexts/AnalysisContext';
import { AuthProvider } from './contexts/AuthContext';
import { AppRouter } from './routes/AppRouter';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AnalysisProvider>
          <BrowserRouter>
            <AppRouter />
            <Toaster
              position="bottom-right"
              toastOptions={{
                style: {
                  background: '#0f172a',
                  color: '#f1f5f9',
                  border: '1px solid rgba(6, 182, 212, 0.3)',
                  fontSize: '13px',
                  fontFamily: 'Inter, sans-serif',
                },
              }}
            />
          </BrowserRouter>
        </AnalysisProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
