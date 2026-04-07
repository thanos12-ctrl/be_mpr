import { useEffect, useState } from 'react';
import { Plus, Edit, Trash2, Eye } from 'lucide-react';
import { fetchSubjects, createSubject, updateSubject, Subject } from '@/services/api';
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
import { toast } from 'sonner';

const SubjectManager = () => {
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [loading, setLoading] = useState(true);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
    const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);
    const [selectedSubject, setSelectedSubject] = useState<Subject | null>(null);
    const [formData, setFormData] = useState({
        subject_id: '',
        name: '',
        description: '',
        icon: '📚',
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        loadSubjects();
    }, []);

    const loadSubjects = async () => {
        try {
            const data = await fetchSubjects();
            setSubjects(data);
        } catch (error) {
            console.error('Failed to load subjects:', error);
            toast.error('Failed to load subjects');
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
            loadSubjects();
        } catch (error: any) {
            console.error('Failed to create subject:', error);
            toast.error(error.response?.data?.detail || 'Failed to create subject');
        } finally {
            setSubmitting(false);
        }
    };

    const handleView = (subject: Subject) => {
        setSelectedSubject(subject);
        setIsViewDialogOpen(true);
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
            loadSubjects();
        } catch (error: any) {
            console.error('Failed to update subject:', error);
            toast.error(error.response?.data?.detail || 'Failed to update subject');
        } finally {
            setSubmitting(false);
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
        <div className="max-w-6xl mx-auto space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Manage Subjects</h1>
                    <p className="text-muted-foreground mt-2">Create and organize your course subjects</p>
                </div>
                <Button onClick={() => setIsDialogOpen(true)} className="bg-gradient-to-r from-primary to-primary-glow">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Subject
                </Button>
            </div>

            {/* Subjects Grid */}
            {subjects.length === 0 ? (
                <Card className="p-12 text-center bg-card border-border">
                    <div className="max-w-md mx-auto">
                        <div className="text-6xl mb-4">📚</div>
                        <h3 className="text-xl font-semibold mb-2">No subjects yet</h3>
                        <p className="text-muted-foreground mb-6">
                            Get started by creating your first subject. Subjects are the main categories for your lessons.
                        </p>
                        <Button onClick={() => setIsDialogOpen(true)} className="bg-gradient-to-r from-primary to-primary-glow">
                            <Plus className="h-4 w-4 mr-2" />
                            Create Your First Subject
                        </Button>
                    </div>
                </Card>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {subjects.map((subject) => (
                        <Card key={subject.id} className="p-6 bg-card border-border hover:shadow-[var(--shadow-elevated)] transition-all">
                            <div className="space-y-4">
                                <div className="flex items-start justify-between">
                                    <div className="text-4xl">{subject.icon}</div>
                                    <div className={`px-2 py-1 rounded text-xs ${subject.is_published
                                        ? 'bg-success/10 text-success'
                                        : 'bg-muted text-muted-foreground'
                                        }`}>
                                        {subject.is_published ? 'Published' : 'Draft'}
                                    </div>
                                </div>

                                <div>
                                    <h3 className="font-semibold text-lg mb-1">{subject.name}</h3>
                                    <p className="text-sm text-muted-foreground line-clamp-2">{subject.description}</p>
                                </div>

                                <div className="flex items-center space-x-2 pt-4 border-t border-border">
                                    <Button variant="outline" size="sm" className="flex-1" onClick={() => handleView(subject)}>
                                        <Eye className="h-4 w-4 mr-1" />
                                        View
                                    </Button>
                                    <Button variant="outline" size="sm" className="flex-1" onClick={() => handleEdit(subject)}>
                                        <Edit className="h-4 w-4 mr-1" />
                                        Edit
                                    </Button>
                                </div>
                            </div>
                        </Card>
                    ))}
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
                            <Button type="submit" disabled={submitting} className="bg-gradient-to-r from-primary to-primary-glow">
                                {submitting ? 'Creating...' : 'Create Subject'}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* View Subject Dialog */}
            <Dialog open={isViewDialogOpen} onOpenChange={setIsViewDialogOpen}>
                <DialogContent className="sm:max-w-[500px]">
                    <DialogHeader>
                        <DialogTitle>Subject Details</DialogTitle>
                        <DialogDescription>
                            View subject information
                        </DialogDescription>
                    </DialogHeader>

                    {selectedSubject && (
                        <div className="space-y-4 py-4">
                            <div className="flex items-center space-x-4">
                                <div className="text-5xl">{selectedSubject.icon}</div>
                                <div className="flex-1">
                                    <h3 className="text-xl font-semibold">{selectedSubject.name}</h3>
                                    <p className="text-sm text-muted-foreground">ID: {selectedSubject.subject_id}</p>
                                </div>
                                <div className={`px-3 py-1 rounded text-sm ${selectedSubject.is_published
                                    ? 'bg-success/10 text-success'
                                    : 'bg-muted text-muted-foreground'
                                    }`}>
                                    {selectedSubject.is_published ? 'Published' : 'Draft'}
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label>Description</Label>
                                <p className="text-sm text-muted-foreground">{selectedSubject.description}</p>
                            </div>

                            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
                                <div>
                                    <Label className="text-xs text-muted-foreground">Created At</Label>
                                    <p className="text-sm">{new Date(selectedSubject.created_at).toLocaleDateString()}</p>
                                </div>
                                <div>
                                    <Label className="text-xs text-muted-foreground">Status</Label>
                                    <p className="text-sm">{selectedSubject.is_published ? 'Published' : 'Draft'}</p>
                                </div>
                            </div>
                        </div>
                    )}

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsViewDialogOpen(false)}>
                            Close
                        </Button>
                        <Button onClick={() => {
                            setIsViewDialogOpen(false);
                            if (selectedSubject) handleEdit(selectedSubject);
                        }}>
                            Edit Subject
                        </Button>
                    </DialogFooter>
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
                            <Button type="submit" disabled={submitting} className="bg-gradient-to-r from-primary to-primary-glow">
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
