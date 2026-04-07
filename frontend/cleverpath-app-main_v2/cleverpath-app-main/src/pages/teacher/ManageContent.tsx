import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, FileText, HelpCircle, Plus, TrendingUp } from 'lucide-react';
import { fetchSubjects, fetchLessons, listQuestions, Subject, Lesson } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const ManageContent = () => {
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [lessons, setLessons] = useState<Lesson[]>([]);
    const [questionCount, setQuestionCount] = useState(0);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadData = async () => {
            try {
                const [subjectsData, lessonsData, questionsData] = await Promise.all([
                    fetchSubjects(),
                    fetchLessons(),
                    listQuestions(),
                ]);
                setSubjects(subjectsData);
                setLessons(lessonsData);
                setQuestionCount(questionsData.length);
            } catch (error) {
                console.error('Failed to load content:', error);
                toast.error('Failed to load content data');
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, []);

    if (loading) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <div className="text-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading content...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Content Management</h1>
                    <p className="text-muted-foreground mt-2">Create and manage subjects, lessons, and quiz questions</p>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid gap-6 md:grid-cols-3">
                <Card className="p-6 bg-card border-border">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Total Subjects</p>
                            <p className="text-3xl font-bold mt-2">{subjects.length}</p>
                        </div>
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                            <BookOpen className="h-6 w-6 text-primary" />
                        </div>
                    </div>
                </Card>

                <Card className="p-6 bg-card border-border">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Total Lessons</p>
                            <p className="text-3xl font-bold mt-2">{lessons.length}</p>
                        </div>
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-secondary/10">
                            <FileText className="h-6 w-6 text-secondary" />
                        </div>
                    </div>
                </Card>

                <Card className="p-6 bg-card border-border">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Total Questions</p>
                            <p className="text-3xl font-bold mt-2">{questionCount}</p>
                        </div>
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10">
                            <HelpCircle className="h-6 w-6 text-accent" />
                        </div>
                    </div>
                </Card>
            </div>

            {/* Quick Actions */}
            <Card className="p-8 bg-card border-border">
                <h2 className="text-2xl font-semibold mb-6">Quick Actions</h2>
                <div className="grid gap-4 md:grid-cols-3">
                    <Link to="/teacher/subjects">
                        <Button className="w-full h-auto flex-col py-6 bg-gradient-to-br from-primary/10 to-primary/5 hover:from-primary/20 hover:to-primary/10 border-2 border-primary/20">
                            <BookOpen className="h-8 w-8 mb-2 text-primary" />
                            <span className="text-base font-semibold">Manage Subjects</span>
                            <span className="text-xs text-muted-foreground mt-1">Create and edit subjects</span>
                        </Button>
                    </Link>

                    <Link to="/teacher/lessons">
                        <Button className="w-full h-auto flex-col py-6 bg-gradient-to-br from-secondary/10 to-secondary/5 hover:from-secondary/20 hover:to-secondary/10 border-2 border-secondary/20">
                            <FileText className="h-8 w-8 mb-2 text-secondary" />
                            <span className="text-base font-semibold">Manage Lessons</span>
                            <span className="text-xs text-muted-foreground mt-1">Create and edit lessons</span>
                        </Button>
                    </Link>

                    <Link to="/teacher/questions">
                        <Button className="w-full h-auto flex-col py-6 bg-gradient-to-br from-accent/10 to-accent/5 hover:from-accent/20 hover:to-accent/10 border-2 border-accent/20">
                            <HelpCircle className="h-8 w-8 mb-2 text-accent" />
                            <span className="text-base font-semibold">Question Bank</span>
                            <span className="text-xs text-muted-foreground mt-1">Manage quiz questions</span>
                        </Button>
                    </Link>
                </div>
            </Card>

            {/* Recent Subjects */}
            <Card className="p-8 bg-card border-border">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-semibold">My Subjects</h2>
                    <Link to="/teacher/subjects">
                        <Button variant="outline" size="sm">
                            <Plus className="h-4 w-4 mr-2" />
                            Create Subject
                        </Button>
                    </Link>
                </div>

                {subjects.length === 0 ? (
                    <div className="text-center py-12">
                        <BookOpen className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                        <p className="text-muted-foreground">No subjects yet</p>
                        <Link to="/teacher/subjects">
                            <Button className="mt-4">
                                <Plus className="h-4 w-4 mr-2" />
                                Create Your First Subject
                            </Button>
                        </Link>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {subjects.slice(0, 5).map((subject) => {
                            const subjectLessons = lessons.filter((l) => l.subject_id === subject.id);
                            return (
                                <Link key={subject.id} to={`/teacher/subjects/${subject.id}`}>
                                    <Card className="p-4 hover:shadow-[var(--shadow-elevated)] transition-all cursor-pointer border-border">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-4">
                                                <div className="text-3xl">{subject.icon}</div>
                                                <div>
                                                    <h3 className="font-semibold">{subject.name}</h3>
                                                    <p className="text-sm text-muted-foreground">{subject.description}</p>
                                                    <div className="flex items-center space-x-4 mt-2 text-xs text-muted-foreground">
                                                        <span>{subjectLessons.length} lessons</span>
                                                        <span className={subject.is_published ? 'text-success' : 'text-muted-foreground'}>
                                                            {subject.is_published ? '● Published' : '○ Draft'}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                            <TrendingUp className="h-5 w-5 text-muted-foreground" />
                                        </div>
                                    </Card>
                                </Link>
                            );
                        })}
                    </div>
                )}
            </Card>
        </div>
    );
};

export default ManageContent;
