# -*- coding: utf-8 -*-

import json
from datetime import timedelta

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
from geopy.distance import geodesic

class PopsMeasurement(models.Model):
    _name = 'pops.measurement'
    _description = 'Measurement'
    _order = 'priority desc, sequence, id desc'
    
    name = fields.Char('Name')
    user_id = fields.Many2one('res.users', 'User', readonly=True,                              
                              default=lambda self: self.env.uid)    
    state = fields.Selection([('draft','Draft'),('ordered','Ordered'),('doing','Doing'),('done','Done')],
        default='draft',string='State')
    date_started = fields.Date('Date Started')
    date_finished = fields.Date('Date Finished')
    measurement_latitude = fields.Float('Geo Latitude', digits=(16, 5))
    measurement_longitude = fields.Float('Geo Longitude', digits=(16, 5))
    google_map_measurement = fields.Char(string='Map')
    lines_ids = fields.One2many('pops.measurement.lines', 'measurement_id', 'Measurement Lines', readonly=True, copy=True)
    quizz_lines_ids = fields.One2many('pops.measurement.quizzlines', 'measurement_id', 'Measurement Quizz Lines', readonly=True, copy=True)
    photo_lines_ids = fields.One2many('pops.measurement.photolines', 'measurement_id', 'Measurement Photo Lines', readonly=True, copy=True)
    missions_id = fields.Many2one('pops.missions','Missions', ondelete='cascade', required=True)
    color = fields.Integer(string='Color Index')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ], default='0', index=True, string='Priority')
    sequence = fields.Integer(string='Sequence', index=True, default=10,
        help='Gives the sequence order when displaying a list of measurement.')
    active = fields.Boolean(default=True)
    kanban_state = fields.Selection([
        ('draft', 'Grey'),
        ('ordered', 'Yellow'),
        ('doing', 'Green'),
        ('done', 'Blue')], string='Kanban State',
        copy=False, default='draft', required=True)
    kanban_state_label = fields.Char(compute='_compute_kanban_state_label', string='Kanban State Label', 
        track_visibility='onchange')
    legend_priority = fields.Char(
        string='Starred Explanation', translate=True,
        help='Explanation text to help users using the star on tasks or issues in this stage.')
    legend_blocked = fields.Char(
        'Yellow Kanban Label', default=lambda s: _('Ready'), translate=True, required=True,
        help='Override the default value displayed for the blocked state for kanban selection, when the task or issue is in that stage.')
    legend_done = fields.Char(
        'Blue Kanban Label', default=lambda s: _('Done'), translate=True, required=True,
        help='Override the default value displayed for the done state for kanban selection, when the task or issue is in that stage.')
    legend_normal = fields.Char(
        'Grey Kanban Label', default=lambda s: _('Pending'), translate=True, required=True,
        help='Override the default value displayed for the normal state for kanban selection, when the task or issue is in that stage.')
    legend_doing = fields.Char(
        'Green Kanban Label', default=lambda s: _('In Progress'), translate=True, required=True,
        help='Override the default value displayed for the normal state for kanban selection, when the task or issue is in that stage.')
    partner_id = fields.Many2one(related='missions_id.partner_id')   
    approved = fields.Boolean(default=False)
    paid = fields.Boolean(default=False)

    @api.onchange('measurement_latitude', 'measurement_longitude')
    def compute_get_google_map(self):
        #maps_loc = {u'position': {u'lat': self.measurement_latitude, u'lng': self.measurement_longitude}, u'zoom': 3}
        #maps_loc = {u'position': {u'lat': 20.593684, u'lng': 78.96288}, u'zoom': 3}
        maps_loc = {
                    u'position': {u'lat': self.measurement_latitude, u'lng': self.measurement_longitude},        
                    u'zoom': 3
                    }
        json_map = json.dumps(maps_loc)
        self.google_map_measurement = json_map    

    
    @api.depends('state', 'kanban_state')
    def _compute_kanban_state_label(self):
        for task in self:
            if task.kanban_state == 'draft':
                task.kanban_state_label = task.legend_normal
            elif task.kanban_state == 'ordered':
                task.kanban_state_label = task.legend_blocked
            elif task.kanban_state == 'doing':
                task.kanban_state_label = task.legend_blocked                
            else:
                task.kanban_state_label = task.legend_done    
        
class PopsMeasurementLine(models.Model):
    _name = 'pops.measurement.lines'
    _description = 'Measurement Lines' 
    
    name = fields.Char('Quizz/Descriptions')        
    type = fields.Selection([('quizz','Quizz'),('photo','Photo'),('double','Quizz and Photo')], default='quizz', string='Type')
    answer = fields.Text('Answer')
    photo = fields.Binary('Photo')
    photo_name = fields.Char('Photo Name')
    measurement_id = fields.Many2one('pops.measurement', 'Measurement', ondelete='cascade', required=True)

class PopsMeasurementQuizzLine(models.Model):
    _name = 'pops.measurement.quizzlines'
    _description = 'Measurement Quizz Lines' 
    
    name = fields.Char('Quizz Answers')
    quizz_id = fields.Many2one('pops.quizz', 'Quizz', ondelete='cascade', required=True)
    alternative_id = fields.Many2one('pops.alternative', 'Alternative', ondelete='cascade', required=True)
    measurement_id = fields.Many2one('pops.measurement', 'Measurement', ondelete='cascade', required=True)

class PopsMeasurementPhotoLine(models.Model):
    _name = 'pops.measurement.photolines'
    _description = 'Measurement Photo Lines' 

    name = fields.Char('Photo Name')
    photo = fields.Binary('Photo')
    photo_id = fields.Many2one('pops.photo.lines', 'Photo Line', ondelete='cascade', required=True)
    measurement_id = fields.Many2one('pops.measurement', 'Measurement', ondelete='cascade', required=True)

class PopsMissions(models.Model):
    _name = 'pops.missions'
    _description = 'Missions'

    @api.multi
    def _compute_measurement_count(self):
        measurement = self.env['pops.measurement']
        for missions in self:
            missions.measurement_count = measurement.search_count([('missions_id', '=', missions.id)])
            print('_compute_measurement_count ', missions.measurement_count)

    # @api.multi
    # def _compute_rewarded_count(self):
    #     measurement = self.env['pops.measurement']
    #     for missions in self:
    #         rewards = 0.0
    #         measurement.search([('approved', '=', True)], limit=1).
    #         missions.rewarded_count = measurement.search_count([
    #             ('missions_id', '=', missions.id), 
    #             ('approved', '=', True)])

    # @api.multi
    # def _compute_paid_count(self):
    #     measurement = self.env['pops.measurement']
    #     for missions in self:
    #         missions.paid_count = measurement.search_count([
    #             ('missions_id', '=', missions.id), 
    #             ('approved', '=', True),
    #             ('paid', '=', True)])

    name = fields.Char('Mission Title', required=True)
    state = fields.Selection([('draft','Draft'),('open','Open'),('reopen','Re-Open'),('close','Close')],
        default='draft',string='State')    
    create_by_user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.uid)
    partner_id = fields.Many2one('res.partner', 'Partner')
    subject = fields.Char('Subject')
    instructions = fields.Text('Instructions')
    type_mission = fields.Selection([('quizz','Quizz'),('photo','Photo'),('double','Quizz and Photo')],
        default='quizz', string='Type')
    date_create = fields.Date('Date Start')
    date_finished = fields.Date('Date Finished')
    closed = fields.Boolean('Closed?')    
    email = fields.Char('e-mail')
    priority = fields.Integer('Priority')
    account_anality = fields.Char('Account Anality')   
    contract = fields.Char('Contract')
    mission_map = fields.Char(string='Map')
    limit = fields.Integer('Limit') 
    scores = fields.Float(string='Scores')
    reward = fields.Float(string='Reward')
    photo_ids = fields.One2many('pops.photo.lines', 'mission_id', 'Photo Lines', readonly=True, copy=True)
    quizz_ids = fields.One2many('pops.quizz', 'missions_id', 'Quizz Lines', readonly=True, copy=True)
    measurement_count = fields.Integer(compute='_compute_measurement_count', string='Measurement Count', type='integer', 
                                                      groups='ps_missions.group_missions_user')
    establishment_id=fields.Many2one('pops.establishment', 'Establishment', ondelete='cascade', required=True)
    # reward_count = fields.Float(compute='_compute_reward_count', string='Reward', type='float', 
                                                      #groups='ps_missions.group_missions_user')
    
    # def _calculate_distance(self):
    #     origin = (30.172705, 31.526725)  # (latitude, longitude) don't confuse
    #     dist = (30.288281, 31.732326)

    #     # print(geodesic(origin, dist).meters)  # 23576.805481751613
    #     # print(geodesic(origin, dist).miles)  # 14.64994773134371
    #     return geodesic(origin, dist).kilometers)  # 23.576805481751613
        

class PopsPhotoLine(models.Model):
    _name = 'pops.photo.lines'
    _description = 'Photo Lines' 
    
    name = fields.Char(string='Descrição')
    mission_id = fields.Many2one('pops.missions', 'Mission', ondelete='cascade', required=True)

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'


    @api.multi
    def _compute_missions_count(self):
        missions = self.env['pops.missions']
        for partner in self:
            partner.missions_count = missions.search_count([('partner_id', '=', partner.id)])
            
    missions_count = fields.Integer(compute='_compute_missions_count', string='Missions Count', type='integer', 
                                    groups='ps_missions.group_missions_user')   

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        user = super(ResUsers, self.with_context(no_reset_password=True)).create(vals)

        return user

class PopsAlternative(models.Model):
    _name = 'pops.alternative'
    _description = 'Alternative'

    name = fields.Char('Text')

class PopsQuizz(models.Model):
    _name = 'pops.quizz'
    _description = 'Quizz'

    name = fields.Char('Question')
    quizz_line_ids = fields.One2many('pops.quizz.lines', 'quizz_id', 'Quizz Lines', readonly=True, copy=True)
    missions_id = fields.Many2one('pops.missions','Missions', ondelete='cascade', required=True)

class PopsQuizzLine(models.Model):
    _name = 'pops.quizz.lines'
    _description = 'Quizz Lines' 
        
    alternative_id = fields.Many2one('pops.alternative', 'Alternative', ondelete='cascade', required=True)
    correct = fields.Boolean('Is Correct?')
    quizz_id = fields.Many2one('pops.quizz', 'Quizz', ondelete='cascade', required=True)


class PopsEstablishment(models.Model):
    _name = 'pops.establishment'
    _description = 'Establishment'

    name = fields.Char('Name', required=True)
    zip_code = fields.Char('Zip Code')
    address = fields.Char('Address')
    neighbor = fields.Char('Neighbor')
    city = fields.Char('City')
    state = fields.Char('State')
    latitude = fields.Char('Latitude')
    longitude = fields.Char('Longitude')
    