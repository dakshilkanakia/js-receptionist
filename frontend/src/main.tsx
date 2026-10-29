import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import Home from './pages/Home'
import CallDetailPage from './pages/owner/CallDetail'
import CallbacksPage from './pages/owner/Callbacks'
import CallsPage from './pages/owner/Calls'
import FactsPage from './pages/owner/Facts'
import OwnerLayout from './pages/owner/Layout'
import LoginPage from './pages/owner/Login'
import OverviewPage from './pages/owner/Overview'
import QuestionsPage from './pages/owner/Questions'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: true } },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/owner/login" element={<LoginPage />} />
          <Route path="/owner" element={<OwnerLayout />}>
            <Route index element={<OverviewPage />} />
            <Route path="calls" element={<CallsPage />} />
            <Route path="calls/:id" element={<CallDetailPage />} />
            <Route path="callbacks" element={<CallbacksPage />} />
            <Route path="questions" element={<QuestionsPage />} />
            <Route path="facts" element={<FactsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
