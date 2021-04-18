					.cpu		sh2
					.endian		big
;					.output		dbg
;
; Variables
f_typew_fx			.assign h'0606efdc
					.section main,code,locate=h'0607C8D8
f_sound_delay:
					sts.l 	pr, @-r15
					mov.l 	literal, r1
					mov.b 	@r1, r0
					tst 	r0, r0
					bf 		loc_skip
					mov 	#1, r0
					mov.b 	r0, @r1
					mov.l 	#f_typew_fx, r0
					jsr 	@r0
					nop
					bra 	loc_rtn
loc_skip:
					mov 	#0, r0
					mov.b 	r0, @r1
loc_rtn:
					lds.l 	@r15+, pr
					rts
					nop
literal:
					.data.l	var
					.section data1,data,align=4
var:
					.data.b h'00
					.end