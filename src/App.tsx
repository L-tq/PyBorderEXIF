import { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import StepIndicator from './components/StepIndicator';
import FileUploadPage from './pages/FileUploadPage';
import LayoutEditorPage from './pages/LayoutEditorPage';
import ReviewPage from './pages/ReviewPage';
import { usePersistence } from './hooks/usePersistence';
import { loadSettings } from './utils/cookies';

function AppContent() {
  const [authorName, setAuthorName] = useState(() => {
    const saved = loadSettings();
    return saved?.defaultAuthor || '';
  });

  usePersistence(authorName);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <StepIndicator />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<FileUploadPage />} />
          <Route
            path="/edit"
            element={
              <LayoutEditorPage
                authorName={authorName}
                onAuthorChange={setAuthorName}
              />
            }
          />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
