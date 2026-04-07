// API Service for Adaptive Learning Platform - Backend Integration
import axios from 'axios';
import { API_BASE_URL } from '@/config';

// ==========================================
// AXIOS INSTANCE WITH INTERCEPTORS
// ==========================================

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token } = response.data;
          localStorage.setItem('access_token', access_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// ==========================================
// TYPE DEFINITIONS
// ==========================================

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'student' | 'teacher' | 'admin';
  created_at: string;
  last_login: string | null;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Subject {
  id: string;
  subject_id: string;
  name: string;
  description: string;
  icon: string;
  is_published: boolean;
  created_by: string | null;
  created_at: string;
}

export interface Lesson {
  id: string;
  subject_id: string;
  lesson_number: number;
  title: string;
  slug: string;
  introduction: string;
  code_example: string | null;
  key_takeaways: string[];
  estimated_time_minutes: number;
  difficulty_level: number;
  prerequisites: string[];
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface Enrollment {
  id: string;
  student_id: string;
  subject_id: string;
  enrolled_at: string;
  completed_at: string | null;
  rl_enabled: boolean;
}

export interface QuizQuestion {
  question_id: string;
  question_text: string;
  code: string | null;
  options: { [key: string]: string };
  part: number;
  concept: string;
  difficulty: number;
  lstm_confidence: number;
  step: number;
  total_steps: number;
}

export interface QuizFeedback {
  is_correct: boolean;
  correct_answer: string;
  explanation: string;
  reward: number;
  reward_breakdown: { [key: string]: number };
  consecutive_correct: number;
  consecutive_wrong: number;
  should_continue: boolean;
  next_question: QuizQuestion | null;
}

export interface QuizProgress {
  session_id: string;
  subject: string;
  total_questions_answered: number;
  overall_accuracy: number;
  concept_mastery: { [key: string]: number };
  difficulty_progression: number[];
  learning_trajectory: any[];
  total_reward: number;
  time_spent_seconds: number;
}

export interface ProgressOverview {
  total_lessons: number;
  completed_lessons: number;
  total_quizzes: number;
  completed_quizzes: number;
  average_quiz_score: number;
  total_time_spent_seconds: number;
  current_streak_days: number;
}

export interface StudentProgress {
  student_id: string;
  student_name: string;
  student_email: string;
  enrollment_id: string;
  subject_id: string;
  subject_name: string;
  lessons_completed: number;
  quizzes_completed: number;
  average_score: number;
  total_time_seconds: number;
  last_activity: string | null;
  rl_enabled: boolean;
}

// ==========================================
// AUTHENTICATION
// ==========================================

export const loginUser = async (email: string, password: string): Promise<TokenResponse> => {
  const response = await api.post('/api/auth/login', { email, password });
  return response.data;
};

export const registerUser = async (
  email: string,
  password: string,
  full_name: string,
  role: 'student' | 'teacher'
): Promise<TokenResponse> => {
  const response = await api.post('/api/auth/register', {
    email,
    password,
    full_name,
    role,
  });
  return response.data;
};

export const refreshAccessToken = async (refreshToken: string): Promise<{ access_token: string }> => {
  const response = await api.post('/api/auth/refresh', { refresh_token: refreshToken });
  return response.data;
};

export const getCurrentUser = async (): Promise<User> => {
  const response = await api.get('/api/auth/me');
  return response.data;
};

// ==========================================
// SUBJECTS & LESSONS
// ==========================================

export const fetchSubjects = async (): Promise<Subject[]> => {
  const response = await api.get('/api/subjects/published');
  return response.data;
};

export const fetchLessons = async (subjectId?: string): Promise<Lesson[]> => {
  const params = subjectId ? { subject_id: subjectId } : {};
  const response = await api.get('/api/lessons', { params });
  return response.data;
};

// Create a new subject
export const createSubject = async (subjectData: { subject_id: string; name: string; description: string; icon: string }): Promise<Subject> => {
  const response = await api.post('/api/admin/subjects', subjectData);
  return response.data;
};

// Update an existing subject
export const updateSubject = async (id: string, data: {
  name?: string;
  description?: string;
  icon?: string;
  is_published?: boolean;
}): Promise<Subject> => {
  const response = await api.put(`/api/admin/subjects/${id}`, data);
  return response.data;
};

// Create a new lesson
export const createLesson = async (lessonData: any): Promise<Lesson> => {
  const response = await api.post('/api/lessons', lessonData);
  return response.data;
};

export const fetchLessonById = async (lessonId: string): Promise<Lesson> => {
  const response = await api.get(`/api/lessons/${lessonId}`);
  return response.data;
};

// ==========================================
// ENROLLMENTS
// ==========================================

export const enrollInSubject = async (subjectId: string): Promise<Enrollment> => {
  const response = await api.post('/api/enrollments', {
    subject_id: subjectId,
    // rl_enabled defaults to true on backend, controlled by teachers
  });
  return response.data;
};

export const getMyCourses = async (): Promise<Enrollment[]> => {
  const response = await api.get('/api/enrollments/my-courses');
  return response.data;
};

// ==========================================
// PROGRESS TRACKING
// ==========================================

export const updateLessonProgress = async (
  lessonId: string,
  timeSpentSeconds: number,
  lastPosition?: string,
  isCompleted: boolean = false
): Promise<void> => {
  await api.post('/api/progress/lessons', {
    lesson_id: lessonId,
    time_spent_seconds: timeSpentSeconds,
    last_position: lastPosition,
    is_completed: isCompleted,
  });
};

export const getProgressOverview = async (): Promise<ProgressOverview> => {
  const response = await api.get('/api/progress/overview');
  return response.data;
};

// ==========================================
// QUIZ SESSIONS (Adaptive Learning)
// ==========================================

export const startQuizSession = async (
  subject: string,
  studentId?: string,
  maxQuestions: number = 10
): Promise<{ session_id: string; subject: string; current_step: number; max_steps: number }> => {
  const response = await api.post('/api/session/start', {
    subject,
    student_id: studentId,
    max_questions: maxQuestions,
  });
  return response.data;
};

export const startLessonQuizSession = async (
  lessonId: string,
  maxQuestions: number = 10
): Promise<{ session_id: string; subject: string; current_step: number; max_steps: number }> => {
  const response = await api.post('/api/session/start-lesson', null, {
    params: {
      lesson_id: lessonId,
      max_questions: maxQuestions,
    },
  });
  return response.data;
};


export const getNextQuestion = async (sessionId: string): Promise<QuizQuestion> => {
  const response = await api.get(`/api/session/${sessionId}/next-question`);
  return response.data;
};

export const submitAnswer = async (
  sessionId: string,
  questionId: string,
  userAnswer: string,
  timeElapsedMs: number
): Promise<QuizFeedback> => {
  const response = await api.post('/api/session/submit-answer', {
    session_id: sessionId,
    question_id: questionId,
    user_answer: userAnswer,
    time_elapsed_ms: timeElapsedMs,
  });
  return response.data;
};

export const getQuizProgress = async (sessionId: string): Promise<QuizProgress> => {
  const response = await api.get(`/api/session/${sessionId}/progress`);
  return response.data;
};

// ==========================================
// TEACHER DASHBOARD
// ==========================================

export const getTeacherStudents = async (): Promise<StudentProgress[]> => {
  const response = await api.get('/api/teacher/students');
  return response.data;
};

export const toggleStudentRL = async (enrollmentId: string, rlEnabled: boolean): Promise<Enrollment> => {
  const response = await api.patch(`/api/enrollments/${enrollmentId}/toggle-rl`, {
    rl_enabled: rlEnabled,
  });
  return response.data;
};

export const createStudentGroup = async (groupName: string): Promise<any> => {
  const response = await api.post('/api/teacher/groups', { group_name: groupName });
  return response.data;
};


// ==========================================
// QUIZ & QUESTION MANAGEMENT (Teacher/Admin)
// ==========================================

export interface QuizCreate {
  lesson_id: string;
  title: string;
  description?: string;
  allow_rl_adaptation?: boolean;
  default_num_questions?: number;
  passing_score?: number;
}

export interface QuizResponse {
  id: string;
  lesson_id: string;
  title: string;
  description: string | null;
  allow_rl_adaptation: boolean;
  default_num_questions: number;
  passing_score: number;
  created_at: string;
}

export interface QuestionCreate {
  quiz_id: string;
  ednet_question_id?: string;
  question_text: string;
  code_snippet?: string;
  options: { A: string; B: string; C: string; D: string };
  correct_answer: string;
  explanation?: string;
  difficulty: number;
  concept: string;
  part: number;
}

export interface QuestionUpdate {
  question_text?: string;
  code_snippet?: string;
  options?: { A: string; B: string; C: string; D: string };
  correct_answer?: string;
  explanation?: string;
  difficulty?: number;
  concept?: string;
}

export interface QuestionResponse {
  id: string;
  quiz_id: string;
  ednet_question_id: string | null;
  question_text: string;
  code_snippet: string | null;
  options: { A: string; B: string; C: string; D: string };
  correct_answer: string;
  explanation: string | null;
  difficulty: number;
  concept: string;
  part: number;
  created_at: string;
}

// Create a new quiz
export const createQuiz = async (quizData: QuizCreate): Promise<QuizResponse> => {
  const response = await api.post('/api/admin/quizzes', quizData);
  return response.data;
};

// List quizzes (optionally filtered by lesson)
export const listQuizzes = async (lessonId?: string): Promise<QuizResponse[]> => {
  const params = lessonId ? { lesson_id: lessonId } : {};
  const response = await api.get('/api/admin/quizzes', { params });
  return response.data;
};

// Create a new question
export const createQuestion = async (questionData: QuestionCreate): Promise<QuestionResponse> => {
  const response = await api.post('/api/admin/questions', questionData);
  return response.data;
};

// List questions (optionally filtered by quiz or concept)
export const listQuestions = async (quizId?: string, concept?: string): Promise<QuestionResponse[]> => {
  const params: any = {};
  if (quizId) params.quiz_id = quizId;
  if (concept) params.concept = concept;
  const response = await api.get('/api/admin/questions', { params });
  return response.data;
};

// Get a specific question
export const getQuestion = async (questionId: string): Promise<QuestionResponse> => {
  const response = await api.get(`/api/admin/questions/${questionId}`);
  return response.data;
};

// Update a question
export const updateQuestion = async (questionId: string, questionData: QuestionUpdate): Promise<QuestionResponse> => {
  const response = await api.put(`/api/admin/questions/${questionId}`, questionData);
  return response.data;
};

// Delete a question
export const deleteQuestion = async (questionId: string): Promise<{ message: string }> => {
  const response = await api.delete(`/api/admin/questions/${questionId}`);
  return response.data;
};


// ==========================================
// LEGACY COMPATIBILITY (for existing pages)
// ==========================================

// Keep these for backward compatibility with existing Quiz/TopicContent pages
export interface Chapter {
  id: string;
  title: string;
  description: string;
  progress: number;
  topicsCount: number;
  difficulty: 'Beginner' | 'Intermediate' | 'Advanced';
}

export interface Topic {
  id: string;
  bundleId: string;
  title: string;
  introduction: string;
  mainContent: string;
  codeExample: string;
  keyPoints: string[];
  videoUrl?: string;
  estimatedTime: number;
}

// Map subjects to chapters format for backward compatibility
export const fetchChapters = async (): Promise<Chapter[]> => {
  const subjects = await fetchSubjects();
  return subjects.map((subject) => ({
    id: subject.id,
    title: subject.name,
    description: subject.description,
    progress: 0, // TODO: Calculate from enrollments
    topicsCount: 0, // TODO: Count lessons
    difficulty: 'Beginner' as const,
  }));
};

// Map lesson to topic format for backward compatibility
export const fetchTopicContent = async (lessonId: string): Promise<Topic> => {
  const lesson = await fetchLessonById(lessonId);
  const formatText = (text: string | null | undefined) => {
    if (!text) return '';
    return text
      .replace(/\\n/g, '\n') // Converts \n string to actual new line
      .replace(/\\"/g, '"'); // Converts \" string to actual quote "
  };
  return {
    id: lesson.id,
    bundleId: lesson.id,
    title: lesson.title,
    introduction: formatText(lesson.introduction),
    mainContent: formatText(lesson.introduction), // Using introduction as main content
    codeExample: formatText(lesson.code_example) || '',
    keyPoints: lesson.key_takeaways,
    estimatedTime: lesson.estimated_time_minutes,
  };
};

// ==========================================
// GROUPS (Teacher)
// ==========================================

export interface Group {
  id: string;
  teacher_id: string;
  group_name: string;
  created_at: string;
  member_count: number;
}

export interface GroupMember {
  student_id: string;
  student_name: string;
  student_email: string;
  added_at: string;
}

export const fetchGroups = async (): Promise<Group[]> => {
  const response = await api.get('/api/teacher/groups');
  return response.data;
};

export const createGroup = async (groupName: string): Promise<Group> => {
  const response = await api.post('/api/teacher/groups', {
    group_name: groupName,
  });
  return response.data;
};

export const fetchGroupMembers = async (groupId: string): Promise<GroupMember[]> => {
  const response = await api.get(`/api/teacher/groups/${groupId}/members`);
  return response.data;
};

export const addStudentToGroup = async (groupId: string, studentId: string): Promise<void> => {
  await api.post(`/api/teacher/groups/${groupId}/students`, {
    student_id: studentId,
  });
};

export const removeStudentFromGroup = async (groupId: string, studentId: string): Promise<void> => {
  await api.delete(`/api/teacher/groups/${groupId}/members/${studentId}`);
};

export const deleteGroup = async (groupId: string): Promise<void> => {
  await api.delete(`/api/teacher/groups/${groupId}`);
};
