import { useEffect, useState } from 'react';
import { Plus, Edit, Trash2, Search } from 'lucide-react';
import {
    listQuizzes,
    listQuestions,
    createQuestion,
    updateQuestion,
    deleteQuestion,
    QuizResponse,
    QuestionResponse,
    QuestionCreate,
    createQuiz,
    fetchLessons,
    Lesson,
} from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { toast } from 'sonner';
import Editor from '@monaco-editor/react';

const QuestionBank = () => {
    const [quizzes, setQuizzes] = useState<QuizResponse[]>([]);
    const [questions, setQuestions] = useState<QuestionResponse[]>([]);
    const [filteredQuestions, setFilteredQuestions] = useState<QuestionResponse[]>([]);
    const [lessons, setLessons] = useState<Lesson[]>([]);
    const [loading, setLoading] = useState(true);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [isQuizDialogOpen, setIsQuizDialogOpen] = useState(false);
    const [editingQuestion, setEditingQuestion] = useState<QuestionResponse | null>(null);
    const [submitting, setSubmitting] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedQuiz, setSelectedQuiz] = useState<string>('all');

    const [quizFormData, setQuizFormData] = useState({
        lesson_id: '',
        title: '',
        description: '',
        default_num_questions: 10,
        allow_rl_adaptation: true,
        passing_score: 0.7,
    });

    const [formData, setFormData] = useState({
        quiz_id: '',
        question_text: '',
        code_snippet: '',
        options: { A: '', B: '', C: '', D: '' },
        correct_answer: 'A',
        explanation: '',
        difficulty: 0.5,
        concept: '',
        part: 1,
    });

    useEffect(() => {
        loadData();
    }, []);

    useEffect(() => {
        filterQuestions();
    }, [searchTerm, selectedQuiz, questions]);

    const loadData = async () => {
        try {
            const [quizzesData, questionsData, lessonsData] = await Promise.all([
                listQuizzes(),
                listQuestions(),
                fetchLessons(),
            ]);
            setQuizzes(quizzesData);
            setQuestions(questionsData);
            setFilteredQuestions(questionsData);
            setLessons(lessonsData);
        } catch (error) {
            console.error('Failed to load data:', error);
            toast.error('Failed to load data');
        } finally {
            setLoading(false);
        }
    };

    const filterQuestions = () => {
        let filtered = questions;

        if (selectedQuiz !== 'all') {
            filtered = filtered.filter((q) => q.quiz_id === selectedQuiz);
        }

        if (searchTerm) {
            filtered = filtered.filter(
                (q) =>
                    q.question_text.toLowerCase().includes(searchTerm.toLowerCase()) ||
                    q.concept.toLowerCase().includes(searchTerm.toLowerCase())
            );
        }

        setFilteredQuestions(filtered);
    };

    const handleOpenDialog = (question?: QuestionResponse) => {
        if (question) {
            setEditingQuestion(question);
            setFormData({
                quiz_id: question.quiz_id,
                question_text: question.question_text,
                code_snippet: question.code_snippet || '',
                options: question.options,
                correct_answer: question.correct_answer,
                explanation: question.explanation || '',
                difficulty: question.difficulty,
                concept: question.concept,
                part: question.part,
            });
        } else {
            setEditingQuestion(null);
            setFormData({
                quiz_id: '',
                question_text: '',
                code_snippet: '',
                options: { A: '', B: '', C: '', D: '' },
                correct_answer: 'A',
                explanation: '',
                difficulty: 0.5,
                concept: '',
                part: 1,
            });
        }
        setIsDialogOpen(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.quiz_id || !formData.question_text || !formData.concept) {
            toast.error('Please fill in all required fields');
            return;
        }

        if (!formData.options.A || !formData.options.B || !formData.options.C || !formData.options.D) {
            toast.error('Please provide all 4 answer options');
            return;
        }

        setSubmitting(true);
        try {
            if (editingQuestion) {
                await updateQuestion(editingQuestion.id, {
                    question_text: formData.question_text,
                    code_snippet: formData.code_snippet || undefined,
                    options: formData.options,
                    correct_answer: formData.correct_answer,
                    explanation: formData.explanation || undefined,
                    difficulty: formData.difficulty,
                    concept: formData.concept,
                });
                toast.success('Question updated successfully!');
            } else {
                await createQuestion({
                    quiz_id: formData.quiz_id,
                    question_text: formData.question_text,
                    code_snippet: formData.code_snippet || undefined,
                    options: formData.options,
                    correct_answer: formData.correct_answer,
                    explanation: formData.explanation || undefined,
                    difficulty: formData.difficulty,
                    concept: formData.concept,
                    part: formData.part,
                });
                toast.success('Question created successfully!');
            }

            setIsDialogOpen(false);
            loadData();
        } catch (error: any) {
            console.error('Failed to save question:', error);
            toast.error(error.response?.data?.detail || 'Failed to save question');
        } finally {
            setSubmitting(false);
        }
    };

    const handleCreateQuizSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!quizFormData.lesson_id || !quizFormData.title) {
            toast.error('Please fill in required fields (Lesson and Title)');
            return;
        }

        setSubmitting(true);
        try {
            await createQuiz(quizFormData);
            toast.success('Quiz created successfully!');
            setIsQuizDialogOpen(false);
            setQuizFormData({
                lesson_id: '',
                title: '',
                description: '',
                default_num_questions: 10,
                allow_rl_adaptation: true,
                passing_score: 0.7,
            });
            loadData();
        } catch (error: any) {
            console.error('Failed to save quiz:', error);
            toast.error(error.response?.data?.detail || 'Failed to create quiz');
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = async (questionId: string) => {
        if (!confirm('Are you sure you want to delete this question?')) return;

        try {
            await deleteQuestion(questionId);
            toast.success('Question deleted successfully!');
            loadData();
        } catch (error) {
            console.error('Failed to delete question:', error);
            toast.error('Failed to delete question');
        }
    };

    if (loading) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <div className="text-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading questions...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                     <h1 className="text-3xl font-bold">Question Bank</h1>
                     <p className="text-muted-foreground mt-2">Manage your quizzes and questions</p>
                 </div>
                 <div className="flex space-x-2">
                     <Button variant="outline" onClick={() => setIsQuizDialogOpen(true)}>
                         <Plus className="h-4 w-4 mr-2" />
                         Create Quiz
                     </Button>
                     <Button onClick={() => handleOpenDialog()} className="bg-gradient-to-r from-primary to-primary-glow">
                         <Plus className="h-4 w-4 mr-2" />
                         Add Question
                     </Button>
                 </div>
             </div>

            {/* Filters */}
            <Card className="p-4 bg-card border-border">
                <div className="flex items-center space-x-4">
                    <div className="flex-1">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search questions or concepts..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="pl-10"
                            />
                        </div>
                    </div>
                    <Select value={selectedQuiz} onValueChange={setSelectedQuiz}>
                        <SelectTrigger className="w-[200px]">
                            <SelectValue placeholder="Filter by quiz" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All Quizzes</SelectItem>
                            {quizzes.map((quiz) => (
                                <SelectItem key={quiz.id} value={quiz.id}>
                                    {quiz.title}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </Card>

            {/* Questions List */}
            {filteredQuestions.length === 0 ? (
                <Card className="p-12 text-center bg-card border-border">
                    <div className="max-w-md mx-auto">
                        <div className="text-6xl mb-4">❓</div>
                        <h3 className="text-xl font-semibold mb-2">No questions found</h3>
                        <p className="text-muted-foreground mb-6">
                            {questions.length === 0
                                ? 'Create your first quiz question to get started.'
                                : 'Try adjusting your search or filter criteria.'}
                        </p>
                        {questions.length === 0 && (
                            <Button onClick={() => handleOpenDialog()} className="bg-gradient-to-r from-primary to-primary-glow">
                                <Plus className="h-4 w-4 mr-2" />
                                Create First Question
                            </Button>
                        )}
                    </div>
                </Card>
            ) : (
                <div className="space-y-4">
                    {filteredQuestions.map((question) => {
                        const quiz = quizzes.find((q) => q.id === question.quiz_id);
                        return (
                            <Card key={question.id} className="p-6 bg-card border-border hover:shadow-[var(--shadow-elevated)] transition-all">
                                <div className="space-y-4">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center space-x-2 mb-2">
                                                <span className="text-xs px-2 py-1 rounded bg-primary/10 text-primary">
                                                    {question.concept}
                                                </span>
                                                <span className="text-xs text-muted-foreground">
                                                    Difficulty: {Math.round(question.difficulty * 100)}%
                                                </span>
                                                {quiz && (
                                                    <span className="text-xs text-muted-foreground">
                                                        Quiz: {quiz.title}
                                                    </span>
                                                )}
                                            </div>
                                            <p className="font-medium">{question.question_text}</p>
                                            {question.code_snippet && (
                                                <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-x-auto">
                                                    <code>{question.code_snippet}</code>
                                                </pre>
                                            )}
                                        </div>
                                        <div className="flex items-center space-x-2 ml-4">
                                            <Button variant="outline" size="sm" onClick={() => handleOpenDialog(question)}>
                                                <Edit className="h-4 w-4" />
                                            </Button>
                                            <Button variant="outline" size="sm" onClick={() => handleDelete(question.id)}>
                                                <Trash2 className="h-4 w-4 text-destructive" />
                                            </Button>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                        {Object.entries(question.options).map(([key, value]) => (
                                            <div
                                                key={key}
                                                className={`p-2 rounded border ${key === question.correct_answer
                                                        ? 'border-success bg-success/5 text-success'
                                                        : 'border-border'
                                                    }`}
                                            >
                                                <strong>{key}:</strong> {value}
                                            </div>
                                        ))}
                                    </div>

                                    {question.explanation && (
                                        <p className="text-sm text-muted-foreground italic">
                                            Explanation: {question.explanation}
                                        </p>
                                    )}
                                </div>
                            </Card>
                        );
                    })}
                </div>
            )}

            {/* Create/Edit Dialog */}
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
                    <form onSubmit={handleSubmit}>
                        <DialogHeader>
                            <DialogTitle>{editingQuestion ? 'Edit Question' : 'Create New Question'}</DialogTitle>
                            <DialogDescription>
                                {editingQuestion ? 'Update the question details below.' : 'Add a new question to your quiz.'}
                            </DialogDescription>
                        </DialogHeader>

                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="quiz">Quiz *</Label>
                                <Select
                                    value={formData.quiz_id}
                                    onValueChange={(value) => setFormData({ ...formData, quiz_id: value })}
                                    disabled={!!editingQuestion}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select a quiz" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {quizzes.map((quiz) => (
                                            <SelectItem key={quiz.id} value={quiz.id}>
                                                {quiz.title}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="question_text">Question Text *</Label>
                                <Textarea
                                    id="question_text"
                                    placeholder="Enter your question..."
                                    value={formData.question_text}
                                    onChange={(e) => setFormData({ ...formData, question_text: e.target.value })}
                                    rows={3}
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <Label>Code Snippet (optional)</Label>
                                <div className="border border-border rounded-lg overflow-hidden">
                                    <Editor
                                        height="150px"
                                        defaultLanguage="java"
                                        value={formData.code_snippet}
                                        onChange={(value) => setFormData({ ...formData, code_snippet: value || '' })}
                                        theme="vs-dark"
                                        options={{
                                            minimap: { enabled: false },
                                            fontSize: 12,
                                        }}
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label>Answer Options *</Label>
                                {(['A', 'B', 'C', 'D'] as const).map((key) => (
                                    <Input
                                        key={key}
                                        placeholder={`Option ${key}`}
                                        value={formData.options[key]}
                                        onChange={(e) =>
                                            setFormData({
                                                ...formData,
                                                options: { ...formData.options, [key]: e.target.value },
                                            })
                                        }
                                        required
                                    />
                                ))}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="correct_answer">Correct Answer *</Label>
                                <Select
                                    value={formData.correct_answer}
                                    onValueChange={(value) => setFormData({ ...formData, correct_answer: value })}
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {['A', 'B', 'C', 'D'].map((option) => (
                                            <SelectItem key={option} value={option}>
                                                Option {option}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="explanation">Explanation (optional)</Label>
                                <Textarea
                                    id="explanation"
                                    placeholder="Explain why this is the correct answer..."
                                    value={formData.explanation}
                                    onChange={(e) => setFormData({ ...formData, explanation: e.target.value })}
                                    rows={2}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="concept">Concept/Topic *</Label>
                                    <Input
                                        id="concept"
                                        placeholder="e.g., variables, loops"
                                        value={formData.concept}
                                        onChange={(e) => setFormData({ ...formData, concept: e.target.value })}
                                        required
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="part">Part Number</Label>
                                    <Input
                                        id="part"
                                        type="number"
                                        min="1"
                                        value={formData.part}
                                        onChange={(e) => setFormData({ ...formData, part: parseInt(e.target.value) })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label>Difficulty: {Math.round(formData.difficulty * 100)}%</Label>
                                <Slider
                                    value={[formData.difficulty]}
                                    onValueChange={(value) => setFormData({ ...formData, difficulty: value[0] })}
                                    min={0}
                                    max={1}
                                    step={0.1}
                                    className="mt-2"
                                />
                            </div>
                        </div>

                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                                Cancel
                            </Button>
                            <Button type="submit" disabled={submitting} className="bg-gradient-to-r from-primary to-primary-glow">
                                {submitting ? 'Saving...' : editingQuestion ? 'Update Question' : 'Create Question'}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* Create Quiz Dialog */}
            <Dialog open={isQuizDialogOpen} onOpenChange={setIsQuizDialogOpen}>
                <DialogContent className="sm:max-w-[600px]">
                    <form onSubmit={handleCreateQuizSubmit}>
                        <DialogHeader>
                            <DialogTitle>Create New Quiz</DialogTitle>
                            <DialogDescription>
                                Create a quiz for a lesson. You can define the maximum number of selected questions for students.
                            </DialogDescription>
                        </DialogHeader>

                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="quiz_lesson">Lesson *</Label>
                                <Select
                                    value={quizFormData.lesson_id}
                                    onValueChange={(value) => {
                                        const lesson = lessons.find((l) => l.id === value);
                                        setQuizFormData({ 
                                            ...quizFormData, 
                                            lesson_id: value,
                                            title: lesson ? `${lesson.title} - Quiz` : ''
                                        });
                                    }}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select a lesson" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {lessons.map((lesson) => (
                                            <SelectItem key={lesson.id} value={lesson.id}>
                                                Lesson {lesson.lesson_number}: {lesson.title}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="quiz_title">Quiz Title *</Label>
                                <Input
                                    id="quiz_title"
                                    placeholder="e.g., Syntax and Variables Quiz"
                                    value={quizFormData.title}
                                    onChange={(e) => setQuizFormData({ ...quizFormData, title: e.target.value })}
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="quiz_desc">Description</Label>
                                <Textarea
                                    id="quiz_desc"
                                    placeholder="Optional description..."
                                    value={quizFormData.description}
                                    onChange={(e) => setQuizFormData({ ...quizFormData, description: e.target.value })}
                                    rows={2}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="quiz_length">Target Number of Questions (Quiz Length) *</Label>
                                <p className="text-xs text-muted-foreground mb-2">
                                    Students will be served this many questions, dynamically selected from the pool you create using RL.
                                </p>
                                <Input
                                    id="quiz_length"
                                    type="number"
                                    min="1"
                                    max="100"
                                    value={quizFormData.default_num_questions}
                                    onChange={(e) => setQuizFormData({ ...quizFormData, default_num_questions: parseInt(e.target.value) || 1 })}
                                    required
                                />
                            </div>
                        </div>

                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setIsQuizDialogOpen(false)}>
                                Cancel
                            </Button>
                            <Button type="submit" disabled={submitting} className="bg-gradient-to-r from-primary to-primary-glow">
                                {submitting ? 'Creating...' : 'Create Quiz'}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default QuestionBank;
