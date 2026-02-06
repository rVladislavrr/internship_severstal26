from src.db.base import BaseManager
from src.schemes import subjects
from src.models import SubjectsORM


class SubjectsManager(BaseManager[subjects.CreateSubjects, subjects.ReadSubjects, subjects.UpdateSubjects,
                                  SubjectsORM]):

    model = SubjectsORM
    create_schema = subjects.CreateSubjects
    read_schema = subjects.ReadSubjects
    update_schema = subjects.UpdateSubjects


subjects_manager = SubjectsManager()
