# -*- coding: utf-8 -*-

import ast

from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.auth_middleware import login_required, is_proffesor
from api.models import Questions, Users, Answers, LogScoreStudent, LogQuestionUser, Students, ScoreStudent, Courses, \
    Lessons
from api.serializers import QuestionsSerializer, GetQuestionsSerializer


@login_required
@is_proffesor
@api_view(['GET', 'POST'])
def questions_list(request):
    if request.method == 'GET':
        items = Questions.objects.all()
        serializer = QuestionsSerializer(items, many=True)
        return Response(dict(success=True, data=serializer.data))

    elif request.method == 'POST':
        serializer = QuestionsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(dict(success=True, data=serializer.data), status=201)
        return Response(dict(success=False, errors=[serializer.errors]), status=400)


@login_required
@api_view(['GET', 'PUT', 'DELETE'])
def questions_detail(request, pk):
    try:
        item = Questions.objects.get(pk=pk)
    except Questions.DoesNotExist:
        return Response(dict(success=False, errors=['No se encuentra esa pregunta']), status=400)

    if request.method == 'GET':
        serializer = GetQuestionsSerializer(item)
        return Response(dict(success=True, data=serializer.data))

    else:
        return edit_question(request, item)


@is_proffesor
def edit_question(request, item):
    if request.method == 'PUT':
        serializer = QuestionsSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(dict(succes=True, data=serializer.data))
        return Response(dict(success=False, errors=[serializer.errors]), status=400)

    elif request.method == 'DELETE':
        item.delete()
        return Response(status=204)


@login_required
@is_proffesor
@api_view(['GET'])
def questions_by_lesson(request, lesson):
    items = Questions.objects.filter(lessons=lesson)
    serializer = QuestionsSerializer(items, many=True)
    return Response(dict(success=True, data=serializer.data))


@login_required
@api_view(['POST'])
def answer_question(request):
    user_id = request.POST.get('student', '')
    question = request.POST.get('question', '')
    response = ast.literal_eval(request.POST.get('response', ''))
    try:
        LogQuestionUser.objects.get(user=user_id, question=question)
        return Response(dict(success=False, errors=['Esa pregunta ya ha sido contestada']), status=400)
    except LogQuestionUser.DoesNotExist:
        pass
    try:
        item_user = Students.objects.get(pk=user_id)
    except Users.DoesNotExist:
        return Response(dict(success=False, errors=['No existe ese usuario']), status=400)
    try:
        item_question = Questions.objects.get(pk=question)
    except Questions.DoesNotExist:
        return Response(dict(success=False, errors=['No existe esa pregunta']), status=400)

    items_answers = Answers.objects.filter(question=item_question.pk, correct=True)
    if len(items_answers) == 0:
        return Response(dict(success=False, errors=['No existen respuestas para esa pregunta']), status=400)
    if item_question.type == "BO" or item_question.type == "MC1C":
        return validate_question_BO_MC1C(item_user, items_answers, item_question, response)
    elif item_question.type == "MCWC":
        return validate_question_MCWC(item_user, items_answers, item_question, response)
    elif item_question.type == "MCAC":
        return validate_question_MCAC(item_user, items_answers, item_question, response)

    return Response(status=200)


def validate_question_BO_MC1C(item_user, items_answers, item_question, response):
    if items_answers[0].pk == response[0]:
        print True
        LogQuestionUser(user=item_user, question=item_question, lesson=item_question.lessons, correct=True).save()
        return Response(dict(success=True, data="Correcto"))
    else:
        print False
        LogQuestionUser(user=item_user, question=item_question, lesson=item_question.lessons, correct=False).save()
        return Response(dict(success=True, data="Incorrecto"))


def validate_question_MCWC(item_user, items_answers, item_question, response):
    for item_answers in items_answers:
        if item_answers.correct:
            if item_answers.pk in response:
                LogQuestionUser(user=item_user, question=item_question, lesson=item_question.lessons,
                                correct=True).save()
                return Response(dict(success=True, data="Correcto"))
    LogQuestionUser(user=item_user, question=item_question, lesson=item_question.lessons, correct=False).save()
    return Response(dict(success=True, data="Incorrecto"))


def validate_question_MCAC(item_user, items_answers, item_question, response):
    for item_answers in items_answers:
        if item_answers.correct:
            if item_answers.pk in response:
                response.remove(item_answers.pk)
    print len(response)
    if not response:
        LogQuestionUser(user=item_user, question=item_question, lesson=item_question.lessons, correct=True).save()
        return Response(dict(success=True, data="Correcto"))
    else:
        LogQuestionUser(user=item_user, question=item_question, lesson=item_question.lessons, correct=False).save()
        return Response(dict(success=True, data="Incorrecto"))


@login_required
@api_view(['GET'])
def question_for_user(request, student):
    try:
        item_student = Students.objects.get(pk=student)
    except Students.DoesNotExist:
        return Response(dict(success=False, errors=["No existe ese usuario"]), status=400)
    item_score_student = ScoreStudent.objects.get(student=student)
    item_questions_answered_user = LogQuestionUser.objects.filter(user=item_student.pk,
                                                                  lesson=item_score_student.lesson).values_list(
        'question', flat=True)
    item_course = Courses.objects.get(pk=item_score_student.course.pk)
    item_lesson = Lessons.objects.get(pk=item_score_student.lesson.pk)
    questions_not_answered = Questions.objects.filter(lessons=item_score_student.lesson).exclude(
        id__in=item_questions_answered_user)
    if len(questions_not_answered) == 0:
        if item_score_student.score >= item_lesson.approval_score:
            LogScoreStudent(student=item_student, course=item_score_student.course, lesson=item_lesson,
                            score=item_score_student.score).save()
            if item_lesson.next_one is not None:
                ScoreStudent.objects.filter(student=student).update(lesson=item_lesson.next_one,
                                                                    score=0)
                return Response(dict(success=False, data="Has terminado la lección"), status=200)

            else:
                if item_course.next_one is not None:
                    item_first_lesson = Lessons.objects.get(previous_one=None, course=item_course.next_one)
                    ScoreStudent.objects.filter(student=student).update(lesson=item_first_lesson,
                                                                        course=item_course.next_one, score=0)
                    return Response(dict(success=False, data="Has avanzado de curso"), status=200)
                else:
                    return Response(dict(success=False, data="Has terminado todos los cursos"), status=200)
        else:
            return Response(dict(success=False, errors=["No alcancaste los puntos para pasar de lección"]), status=400)
    serializer = QuestionsSerializer(questions_not_answered[0])
    return Response(dict(success=True, data=serializer.data), status=200)


"""
student = models.ForeignKey(Students, on_delete=models.SET_NULL, null=True)
    course = models.ForeignKey(Courses, on_delete=models.SET_NULL, null=True)
    lesson = models.ForeignKey(Lessons, on_delete=models.SET_NULL, null=True)
    score = models.IntegerField(default=0)
    """
