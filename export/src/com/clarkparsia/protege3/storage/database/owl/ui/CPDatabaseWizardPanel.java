/**
 * 
 */
package com.clarkparsia.protege3.storage.database.owl.ui;

import java.net.URI;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

import javax.swing.JTextField;

import com.clarkparsia.protege3.storage.database.owl.CPDatabaseRepository;

import edu.stanford.smi.protege.storage.database.DatabaseProperty;
import edu.stanford.smi.protege.util.Log;
import edu.stanford.smi.protege.util.WizardPage;
import edu.stanford.smi.protegex.owl.model.OWLModel;
import edu.stanford.smi.protegex.owl.repository.Repository;
import edu.stanford.smi.protegex.owl.repository.impl.DatabaseRepository;
import edu.stanford.smi.protegex.owl.ui.repository.wizard.impl.DatabaseWizardPanel;

public class CPDatabaseWizardPanel extends DatabaseWizardPanel {
    private static Logger log = Log.getLogger(CPDatabaseWizardPanel.class);
    private static final long serialVersionUID = 8313995336416582467L;
    
    private EnumMap<DatabaseProperty, JTextField> textMap 
            = new EnumMap<DatabaseProperty, JTextField>(DatabaseProperty.class);
    private WizardPage wizardPage;
    
    public CPDatabaseWizardPanel(WizardPage wizardPage,
                                 OWLModel owlModel) {
        super(wizardPage, owlModel);
    }

    @Override
    public Repository createRepository() {
        try {
            return new CPDatabaseRepository(getText(DatabaseProperty.DRIVER_PROPERTY),
                                            getText(DatabaseProperty.URL_PROPERTY),
                                            getText(DatabaseProperty.USERNAME_PROPERTY),
                                            getText(DatabaseProperty.PASSWORD_PROPERTY));
        }
        catch (SQLException e) {
            if (log.isLoggable(Level.FINE))  {
                log.fine("driver = "  + getText(DatabaseProperty.DRIVER_PROPERTY));
                log.fine("url = " + getText(DatabaseProperty.URL_PROPERTY));
                log.fine("username = " + getText(DatabaseProperty.USERNAME_PROPERTY));
                log.fine("password = " + getText(DatabaseProperty.PASSWORD_PROPERTY));
                log.log(Level.FINE, "Create Repository failed", e);
            }
            return null;
        }
        catch (ClassNotFoundException e) {
            if (log.isLoggable(Level.FINE))  {
                log.fine("driver = "  + getText(DatabaseProperty.DRIVER_PROPERTY));
                log.fine("url = " + getText(DatabaseProperty.URL_PROPERTY));
                log.fine("username = " + getText(DatabaseProperty.USERNAME_PROPERTY));
                log.fine("password = " + getText(DatabaseProperty.PASSWORD_PROPERTY));
                log.log(Level.FINE, "Create Repository failed", e);
            }
            return null; 
        }
    }
    
    protected Map<String, URI> getTableToOntologyMap(Repository rep) {
    	return ((CPDatabaseRepository) rep).getTableToOntologyMap();
    }

}