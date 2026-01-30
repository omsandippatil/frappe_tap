import tap_lms.imgana.submission as m
a = m.get_assignment_context(assignment_id="SC_L4_CA1-Basic")
print(a)


import tap_lms.imgana.submission as m
a = m.get_student_details(name="Test_Hindi", glific_id="1234")
print(a)


assignment_id="SC_L4_CA1-Basic"
assignment = frappe.get_doc("Assignment", assignment_id)
print(assignment.as_dict())


import tap_lms.feedback_handler.audio_creation as ac
text_1 = "तुमची चित्रकला खूप रंगीत आणि छान आहे! उत्तम काम करत राहा!"
text_2 = "ਤੁਹਾਡੀ ਕਲਾ ਰਚਨਾ ਸ਼ਾਨਦਾਰ ਰੰਗਾਂ ਨਾਲ ਹੈ। ਚੰਗਾ ਕੰਮ ਜਾਰੀ ਰੱਖੋ!"
text_3 = "ನಿಮ್ಮ ಚಿತ್ರದಲ್ಲಿ ಹೊಳೆಯುವ ಬಣ್ಣಗಳು ಮತ್ತು ಪುನರಾವೃತ್ತಿಯು ಗಮನ ಸೆಳೆಯುತ್ತವೆ. ಇನ್ನಷ್ಟು ವಿನ್ಯಾಸಗಳನ್ನು ಸೇರಿಸಿ!"
text_4 = "Your Pop Art project effectively uses bright colors. Try exploring more patterns for added interest"
language_name = "Marathi"
submission_id = "12345"
audio_url = ac.generate_feedback_audio(
    text=text_1,
    language_name=language_name,
    submission_id=submission_id
)
print(f"Generated audio URL: {audio_url}")


text_1 = "तुमची चित्रकला खूप रंगीत आणि छान आहे! उत्तम काम करत राहा!"
text_2 = "ਤੁਹਾਡੀ ਕਲਾ ਰਚਨਾ ਸ਼ਾਨਦਾਰ ਰੰਗਾਂ ਨਾਲ ਹੈ। ਚੰਗਾ ਕੰਮ ਜਾਰੀ ਰੱਖੋ!"
text_3 = "ನಿಮ್ಮ ಚಿತ್ರದಲ್ಲಿ ಹೊಳೆಯುವ ಬಣ್ಣಗಳು ಮತ್ತು ಪುನರಾವೃತ್ತಿಯು ಗಮನ ಸೆಳೆಯುತ್ತವೆ. ಇನ್ನಷ್ಟು ವಿನ್ಯಾಸಗಳನ್ನು ಸೇರಿಸಿ!"
text_4 = "Your Pop Art project effectively uses bright colors. Try exploring more patterns for added interest"

generate_feedback_audio(text=text_1, language_name="Marathi", submission_id="12345")
# generate_feedback_audio(text=text_2, language_name="Punjabi", submission_id="12346")
# generate_feedback_audio(text=text_3, language_name="Kannada", submission_id="12347")
# generate_feedback_audio(text=text_4, language_name="English", submission_id="12348")