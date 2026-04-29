import { useEffect, useState } from 'react';
import { Plus, Edit, Trash2, Users, BookOpen } from 'lucide-react';
import { fetchAdminSubjects, createSubject, updateSubject, deleteSubject, fetchLessons, getTeacherStudents, Subject, Lesson, StudentProgress } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

const SubjectManager = () => {
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [lessons, setLessons] = useState<Lesson[]>([]);
    const [students, setStudents] = useState<StudentProgress[]>([]);
    const [loading, setLoading] = useState(true);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
    const [selectedSubject, setSelectedSubject] = useState<Subject | null>(null);
    const [formData, setFormData] = useState({
        subject_id: '',
        name: '',
        description: '',
        icon: '📚',
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [subjectsData, lessonsData, studentsData] = await Promise.all([
                fetchAdminSubjects(),
                fetchLessons(),
                getTeacherStudents()
            ]);
            setSubjects(subjectsData);
            setLessons(lessonsData);
            setStudents(studentsData);
        } catch (error) {
            console.error('Failed to load data:', error);
            toast.error('Failed to load subjects data');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.name || !formData.description) {
            toast.error('Please fill in all required fields');
            return;
        }

        setSubmitting(true);
        try {
            await createSubject({
                subject_id: formData.subject_id || formData.name.toLowerCase().replace(/\s+/g, '-'),
                name: formData.name,
                description: formData.description,
                icon: formData.icon,
            });

            toast.success('Subject created successfully!');
            setIsDialogOpen(false);
            setFormData({ subject_id: '', name: '', description: '', icon: '📚' });
            loadData();
        } catch (error: any) {
            console.error('Failed to create subject:', error);
            toast.error(error.response?.data?.detail || 'Failed to create subject');
        } finally {
            setSubmitting(false);
        }
    };

    const handleEdit = (subject: Subject) => {
        setSelectedSubject(subject);
        setFormData({
            subject_id: subject.subject_id,
            name: subject.name,
            description: subject.description,
            icon: subject.icon,
        });
        setIsEditDialogOpen(true);
    };

    const handleUpdate = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.name || !formData.description || !selectedSubject) {
            toast.error('Please fill in all required fields');
            return;
        }

        setSubmitting(true);
        try {
            await updateSubject(selectedSubject.id, {
                name: formData.name,
                description: formData.description,
                icon: formData.icon,
            });

            toast.success('Subject updated successfully!');
            setIsEditDialogOpen(false);
            setFormData({ subject_id: '', name: '', description: '', icon: '📚' });
            setSelectedSubject(null);
            loadData();
        } catch (error: any) {
            console.error('Failed to update subject:', error);
            toast.error(error.response?.data?.detail || 'Failed to update subject');
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = async (subject: Subject) => {
        if (!confirm(`Are you sure you want to delete "${subject.name}"? This action cannot be undone.`)) {
            return;
        }
        
        try {
            // Note: The API must support deleteSubject, assuming it does
            await deleteSubject(subject.id);
            toast.success('Subject deleted successfully!');
            loadData();
        } catch (error: any) {
            console.error('Failed to delete subject:', error);
            toast.error('Failed to delete subject');
        }
    };

    const commonIcons = ['📚', '💻', '🔬', '🎨', '📊', '🌍', '🎵', '⚡', '🚀', '🧮'];

    if (loading) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <div className="text-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading subjects...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">My Published Subjects</h1>
                    <p className="text-muted-foreground mt-1">Manage and monitor your curriculum offerings.</p>
                </div>
                <Button onClick={() => setIsDialogOpen(true)} className="bg-primary hover:bg-primary/90 text-primary-foreground">
                    <Plus className="h-4 w-4 mr-2" />
                    Create New Subject
                </Button>
            </div>

            {subjects.length === 0 ? (
                <Card className="p-12 text-center bg-card border-border">
                    <div className="max-w-md mx-auto">
                        <div className="text-6xl mb-4">📚</div>
                        <h3 className="text-xl font-semibold mb-2">No subjects yet</h3>
                        <p className="text-muted-foreground mb-6">
                            Get started by creating your first subject.
                        </p>
                        <Button onClick={() => setIsDialogOpen(true)} className="bg-primary text-primary-foreground">
                            <Plus className="h-4 w-4 mr-2" />
                            Create Your First Subject
                        </Button>
                    </div>
                </Card>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {subjects.map((subject) => {
                        const subjectLessonsCount = lessons.filter(l => l.subject_id === subject.id).length;
                        const studentCount = students.filter(s => s.subject_id === subject.id).length;
                        
                        return (
                            <Card key={subject.id} className="overflow-hidden bg-card border-border flex flex-col">
                                <div className="h-40 bg-gradient-to-br from-primary/20 to-accent/20 relative flex items-center justify-center">
                                    <div className="text-6xl">{subject.icon}</div>
                                    <div className="absolute top-3 right-3">
                                        <Badge variant="secondary" className={`bg-background/80 backdrop-blur-sm ${subject.is_published ? 'text-success' : 'text-muted-foreground'}`}>
                                            <span className={`w-2 h-2 rounded-full mr-2 ${subject.is_published ? 'bg-success' : 'bg-muted-foreground'}`}></span>
                                            {subject.is_published ? 'Active' : 'Draft'}
                                        </Badge>
                                    </div>
                                </div>

                                <div className="p-5 flex-1 flex flex-col">
                                    <h3 className="font-semibold text-xl mb-3 line-clamp-1">{subject.name}</h3>
                                    
                                    <div className="flex flex-wrap gap-2 mb-4">
                                        <Badge variant="secondary" className="bg-primary/10 text-primary hover:bg-primary/20 font-normal">
                                            {subject.name.includes('Data') ? 'Intermediate' : 'Beginner'}
                                        </Badge>
                                        <Badge variant="secondary" className="bg-secondary/10 text-secondary hover:bg-secondary/20 font-normal">
                                            Core Tech
                                        </Badge>
                                    </div>

                                    <div className="flex items-center justify-between mt-auto pt-4 border-t border-border text-sm text-muted-foreground mb-4">
                                        <div className="flex items-center space-x-1">
                                            <Users className="h-4 w-4" />
                                            <span>{studentCount} Students</span>
                                        </div>
                                        <div className="flex items-center space-x-1">
                                            <BookOpen className="h-4 w-4" />
                                            <span>{subjectLessonsCount} Lessons</span>
                                        </div>
                                    </div>

                                    <div className="flex items-center space-x-2">
                                        <Button variant="outline" className="flex-1 bg-primary/5 text-primary hover:bg-primary/10 border-primary/20" onClick={() => handleEdit(subject)}>
                                            <Edit className="h-4 w-4 mr-2" />
                                            Edit
                                        </Button>
                                        <Button variant="outline" size="icon" className="text-destructive hover:bg-destructive/10 border-destructive/20 hover:text-destructive" onClick={() => handleDelete(subject)}>
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            </Card>
                        );
                    })}
                </div>
            )}

            {/* Create Subject Dialog */}
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogContent className="sm:max-w-[500px]">
                    <form onSubmit={handleSubmit}>
                        <DialogHeader>
                            <DialogTitle>Create New Subject</DialogTitle>
                            <DialogDescription>
                                Add a new subject to organize your lessons and content.
                            </DialogDescription>
                        </DialogHeader>

                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="name">Subject Name *</Label>
                                <Input
                                    id="name"
                                    placeholder="e.g., Java Programming"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="description">Description *</Label>
                                <Textarea
                                    id="description"
                                    placeholder="Brief description of the subject..."
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    rows={3}
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="subject_id">Subject ID (optional)</Label>
                                <Input
                                    id="subject_id"
                                    placeholder="Auto-generated from name if left empty"
                                    value={formData.subject_id}
                                    onChange={(e) => setFormData({ ...formData, subject_id: e.target.value })}
                                />
                                <p className="text-xs text-muted-foreground">
                                    Used for URL-friendly identification. Leave empty to auto-generate.
                                </p>
                            </div>

                            <div className="space-y-2">
                                <Label>Icon</Label>
                                <div className="flex flex-wrap gap-2">
                                    {commonIcons.map((icon) => (
                                        <button
                                            key={icon}
                                            type="button"
                                            onClick={() => setFormData({ ...formData, icon })}
                                            className={`text-2xl p-2 rounded border-2 transition-all ${formData.icon === icon
                                                ? 'border-primary bg-primary/10'
                                                : 'border-border hover:border-primary/50'
                                                }`}
                                        >
                                            {icon}
                                        </button>
                                    ))}
                                </div>
                                <Input
                                    placeholder="Or enter custom emoji"
                                    value={formData.icon}
                                    onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                                    maxLength={2}
                                    className="mt-2"
                                />
                            </div>
                        </div>

                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                                Cancel
                            </Button>
                            <Button type="submit" disabled={submitting} className="bg-primary">
                                {submitting ? 'Creating...' : 'Create Subject'}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* Edit Subject Dialog */}
            <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
                <DialogContent className="sm:max-w-[500px]">
                    <form onSubmit={handleUpdate}>
                        <DialogHeader>
                            <DialogTitle>Edit Subject</DialogTitle>
                            <DialogDescription>
                                Update subject information
                            </DialogDescription>
                        </DialogHeader>

                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="edit-name">Subject Name *</Label>
                                <Input
                                    id="edit-name"
                                    placeholder="e.g., Java Programming"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="edit-description">Description *</Label>
                                <Textarea
                                    id="edit-description"
                                    placeholder="Brief description of the subject..."
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    rows={3}
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="edit-subject_id">Subject ID</Label>
                                <Input
                                    id="edit-subject_id"
                                    value={formData.subject_id}
                                    disabled
                                    className="bg-muted"
                                />
                                <p className="text-xs text-muted-foreground">
                                    Subject ID cannot be changed after creation
                                </p>
                            </div>

                            <div className="space-y-2">
                                <Label>Icon</Label>
                                <div className="flex flex-wrap gap-2">
                                    {commonIcons.map((icon) => (
                                        <button
                                            key={icon}
                                            type="button"
                                            onClick={() => setFormData({ ...formData, icon })}
                                            className={`text-2xl p-2 rounded border-2 transition-all ${formData.icon === icon
                                                ? 'border-primary bg-primary/10'
                                                : 'border-border hover:border-primary/50'
                                                }`}
                                        >
                                            {icon}
                                        </button>
                                    ))}
                                </div>
                                <Input
                                    placeholder="Or enter custom emoji"
                                    value={formData.icon}
                                    onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                                    maxLength={2}
                                    className="mt-2"
                                />
                            </div>
                        </div>

                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => {
                                setIsEditDialogOpen(false);
                                setFormData({ subject_id: '', name: '', description: '', icon: '📚' });
                                setSelectedSubject(null);
                            }}>
                                Cancel
                            </Button>
                            <Button type="submit" disabled={submitting} className="bg-primary">
                                {submitting ? 'Updating...' : 'Update Subject'}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default SubjectManager;
