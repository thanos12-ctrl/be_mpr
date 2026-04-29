import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import TeacherLayout from "./components/TeacherLayout";
import Index from "./pages/Index";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Chapters from "./pages/Chapters";
import BrowseSubjects from "./pages/BrowseSubjects";
import TopicContent from "./pages/TopicContent";
import Quiz from "./pages/Quiz";
import Results from "./pages/Results";
import StudentProfile from "./pages/StudentProfile";
import SubjectManager from "./pages/teacher/SubjectManager";
import LessonEditor from "./pages/teacher/LessonEditor";
import QuestionBank from "./pages/teacher/QuestionBank";
import GroupManager from "./pages/teacher/GroupManager";
import StudentProgress from "./pages/teacher/StudentProgress";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Index />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected routes */}
            <Route
              path="/browse-subjects"
              element={
                <ProtectedRoute>
                  <Layout>
                    <BrowseSubjects />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/subjects"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Chapters />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/topic/:bundleId"
              element={
                <ProtectedRoute>
                  <Layout>
                    <TopicContent />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/quiz/:bundleId"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Quiz />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/results/:sessionId"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Results />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile/student"
              element={
                <ProtectedRoute requireRole="student">
                  <Layout>
                    <StudentProfile />
                  </Layout>
                </ProtectedRoute>
              }
            />

            {/* Teacher Content Management */}
            <Route
              path="/teacher"
              element={
                <ProtectedRoute requireRole="teacher">
                  <Navigate to="/teacher/subjects" replace />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile/teacher"
              element={
                <ProtectedRoute requireRole="teacher">
                  <Navigate to="/teacher/subjects" replace />
                </ProtectedRoute>
              }
            />
            <Route
              path="/teacher/content"
              element={
                <ProtectedRoute requireRole="teacher">
                  <Navigate to="/teacher/subjects" replace />
                </ProtectedRoute>
              }
            />
            <Route
              path="/teacher/subjects"
              element={
                <ProtectedRoute requireRole="teacher">
                  <TeacherLayout>
                    <SubjectManager />
                  </TeacherLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/teacher/lessons"
              element={
                <ProtectedRoute requireRole="teacher">
                  <TeacherLayout>
                    <LessonEditor />
                  </TeacherLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/teacher/questions"
              element={
                <ProtectedRoute requireRole="teacher">
                  <TeacherLayout>
                    <QuestionBank />
                  </TeacherLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/teacher/progress"
              element={
                <ProtectedRoute requireRole="teacher">
                  <TeacherLayout>
                    <StudentProgress />
                  </TeacherLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/teacher/groups"
              element={
                <ProtectedRoute requireRole="teacher">
                  <TeacherLayout>
                    <GroupManager />
                  </TeacherLayout>
                </ProtectedRoute>
              }
            />

            {/* Legacy route redirects */}
            <Route path="/chapters" element={<Navigate to="/subjects" replace />} />

            {/* Catch-all */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
