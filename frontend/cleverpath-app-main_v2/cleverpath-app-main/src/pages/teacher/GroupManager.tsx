import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Plus, Trash2, UserPlus, UserMinus, ArrowLeft } from 'lucide-react';
import {
    fetchGroups,
    createGroup,
    fetchGroupMembers,
    addStudentToGroup,
    removeStudentFromGroup,
    deleteGroup,
    getTeacherStudents,
    Group,
    GroupMember,
    StudentProgress
} from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
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
import { toast } from 'sonner';

const GroupManager = () => {
    const navigate = useNavigate();
    const [groups, setGroups] = useState<Group[]>([]);
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
    const [groupMembers, setGroupMembers] = useState<GroupMember[]>([]);
    const [allStudents, setAllStudents] = useState<StudentProgress[]>([]);
    const [loading, setLoading] = useState(true);
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [addMemberDialogOpen, setAddMemberDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [newGroupName, setNewGroupName] = useState('');
    const [selectedStudentId, setSelectedStudentId] = useState('');
    const [actionLoading, setActionLoading] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [groupsData, studentsData] = await Promise.all([
                fetchGroups(),
                getTeacherStudents(),
            ]);
            setGroups(groupsData);
            setAllStudents(studentsData);
        } catch (error) {
            console.error('Failed to load data:', error);
            toast.error('Failed to load groups');
        } finally {
            setLoading(false);
        }
    };

    const loadGroupMembers = async (groupId: string) => {
        try {
            const members = await fetchGroupMembers(groupId);
            setGroupMembers(members);
        } catch (error) {
            console.error('Failed to load group members:', error);
            toast.error('Failed to load group members');
        }
    };

    const handleCreateGroup = async () => {
        if (!newGroupName.trim()) {
            toast.error('Please enter a group name');
            return;
        }

        setActionLoading(true);
        try {
            await createGroup(newGroupName);
            toast.success('Group created successfully!');
            setNewGroupName('');
            setCreateDialogOpen(false);
            await loadData();
        } catch (error: any) {
            console.error('Failed to create group:', error);
            toast.error(error.response?.data?.detail || 'Failed to create group');
        } finally {
            setActionLoading(false);
        }
    };

    const handleSelectGroup = async (group: Group) => {
        setSelectedGroup(group);
        await loadGroupMembers(group.id);
    };

    const handleAddMember = async () => {
        if (!selectedGroup || !selectedStudentId) {
            toast.error('Please select a student');
            return;
        }

        setActionLoading(true);
        try {
            await addStudentToGroup(selectedGroup.id, selectedStudentId);
            toast.success('Student added to group!');
            setSelectedStudentId('');
            setAddMemberDialogOpen(false);
            await loadGroupMembers(selectedGroup.id);
            await loadData(); // Refresh to update member counts
        } catch (error: any) {
            console.error('Failed to add student:', error);
            toast.error(error.response?.data?.detail || 'Failed to add student');
        } finally {
            setActionLoading(false);
        }
    };

    const handleRemoveMember = async (studentId: string) => {
        if (!selectedGroup) return;

        setActionLoading(true);
        try {
            await removeStudentFromGroup(selectedGroup.id, studentId);
            toast.success('Student removed from group');
            await loadGroupMembers(selectedGroup.id);
            await loadData();
        } catch (error: any) {
            console.error('Failed to remove student:', error);
            toast.error(error.response?.data?.detail || 'Failed to remove student');
        } finally {
            setActionLoading(false);
        }
    };

    const handleDeleteGroup = async () => {
        if (!selectedGroup) return;

        setActionLoading(true);
        try {
            await deleteGroup(selectedGroup.id);
            toast.success('Group deleted successfully');
            setDeleteDialogOpen(false);
            setSelectedGroup(null);
            setGroupMembers([]);
            await loadData();
        } catch (error: any) {
            console.error('Failed to delete group:', error);
            toast.error(error.response?.data?.detail || 'Failed to delete group');
        } finally {
            setActionLoading(false);
        }
    };

    // Filter out students already in the selected group
    const availableStudents = allStudents.filter(
        student => !groupMembers.some(member => member.student_id === student.student_id)
    );

    if (loading) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <div className="text-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading groups...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="space-y-2">
                    <Button
                        variant="ghost"
                        onClick={() => navigate('/profile/teacher')}
                        className="mb-2"
                    >
                        <ArrowLeft className="h-4 w-4 mr-2" />
                        Back to Profile
                    </Button>
                    <h1 className="text-4xl font-bold tracking-tight">Student Groups</h1>
                    <p className="text-xl text-muted-foreground">
                        Organize your students into groups for better management
                    </p>
                </div>
                <Button
                    onClick={() => setCreateDialogOpen(true)}
                    className="bg-gradient-to-r from-primary to-primary-glow"
                >
                    <Plus className="h-4 w-4 mr-2" />
                    Create Group
                </Button>
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
                {/* Groups List */}
                <div className="lg:col-span-1 space-y-4">
                    <h2 className="text-2xl font-semibold">Your Groups</h2>
                    {groups.length === 0 ? (
                        <Card className="p-8 text-center">
                            <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                            <p className="text-muted-foreground">No groups yet</p>
                            <p className="text-sm text-muted-foreground mt-2">
                                Create a group to get started
                            </p>
                        </Card>
                    ) : (
                        <div className="space-y-3">
                            {groups.map((group) => (
                                <Card
                                    key={group.id}
                                    className={`p-4 cursor-pointer transition-all hover:shadow-md ${selectedGroup?.id === group.id
                                        ? 'border-primary bg-primary/5'
                                        : 'border-border'
                                        }`}
                                    onClick={() => handleSelectGroup(group)}
                                >
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <h3 className="font-semibold">{group.group_name}</h3>
                                            <p className="text-sm text-muted-foreground">
                                                {new Date(group.created_at).toLocaleDateString()}
                                            </p>
                                        </div>
                                        <Badge variant="outline">
                                            {group.member_count} {group.member_count === 1 ? 'member' : 'members'}
                                        </Badge>
                                    </div>
                                </Card>
                            ))}
                        </div>
                    )}
                </div>

                {/* Group Details */}
                <div className="lg:col-span-2">
                    {selectedGroup ? (
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <h2 className="text-2xl font-semibold">{selectedGroup.group_name}</h2>
                                <div className="flex space-x-2">
                                    <Button
                                        variant="outline"
                                        onClick={() => setAddMemberDialogOpen(true)}
                                        disabled={availableStudents.length === 0}
                                    >
                                        <UserPlus className="h-4 w-4 mr-2" />
                                        Add Student
                                    </Button>
                                    <Button
                                        variant="destructive"
                                        onClick={() => setDeleteDialogOpen(true)}
                                    >
                                        <Trash2 className="h-4 w-4 mr-2" />
                                        Delete Group
                                    </Button>
                                </div>
                            </div>

                            {groupMembers.length === 0 ? (
                                <Card className="p-8 text-center">
                                    <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                                    <p className="text-muted-foreground">No members in this group</p>
                                    <p className="text-sm text-muted-foreground mt-2">
                                        Add students to get started
                                    </p>
                                </Card>
                            ) : (
                                <div className="space-y-3">
                                    {groupMembers.map((member) => (
                                        <Card key={member.student_id} className="p-4">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <h3 className="font-semibold">{member.student_name}</h3>
                                                    <p className="text-sm text-muted-foreground">{member.student_email}</p>
                                                    <p className="text-xs text-muted-foreground mt-1">
                                                        Added {new Date(member.added_at).toLocaleDateString()}
                                                    </p>
                                                </div>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleRemoveMember(member.student_id)}
                                                    disabled={actionLoading}
                                                >
                                                    <UserMinus className="h-4 w-4 mr-2" />
                                                    Remove
                                                </Button>
                                            </div>
                                        </Card>
                                    ))}
                                </div>
                            )}
                        </div>
                    ) : (
                        <Card className="p-12 text-center">
                            <Users className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                            <h3 className="text-xl font-semibold mb-2">Select a Group</h3>
                            <p className="text-muted-foreground">
                                Choose a group from the list to view and manage its members
                            </p>
                        </Card>
                    )}
                </div>
            </div>

            {/* Create Group Dialog */}
            <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Create New Group</DialogTitle>
                        <DialogDescription>
                            Create a group to organize your students
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="groupName">Group Name</Label>
                            <Input
                                id="groupName"
                                placeholder="e.g., Class 10A, Advanced Learners"
                                value={newGroupName}
                                onChange={(e) => setNewGroupName(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleCreateGroup()}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button onClick={handleCreateGroup} disabled={actionLoading}>
                            {actionLoading ? 'Creating...' : 'Create Group'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Add Member Dialog */}
            <Dialog open={addMemberDialogOpen} onOpenChange={setAddMemberDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Add Student to {selectedGroup?.group_name}</DialogTitle>
                        <DialogDescription>
                            Select a student to add to this group
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="student">Student</Label>
                            <Select value={selectedStudentId} onValueChange={setSelectedStudentId}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select a student" />
                                </SelectTrigger>
                                <SelectContent>
                                    {availableStudents.map((student) => (
                                        <SelectItem key={student.student_id} value={student.student_id}>
                                            {student.student_name} ({student.student_email})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setAddMemberDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button onClick={handleAddMember} disabled={actionLoading}>
                            {actionLoading ? 'Adding...' : 'Add Student'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Group Dialog */}
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Delete Group</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to delete "{selectedGroup?.group_name}"? This action cannot be undone.
                            All members will be removed from the group.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button variant="destructive" onClick={handleDeleteGroup} disabled={actionLoading}>
                            {actionLoading ? 'Deleting...' : 'Delete Group'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default GroupManager;
